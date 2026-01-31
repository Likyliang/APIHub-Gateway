"""
Proxy Routes - Forward requests to upstream CLIProxyAPI
"""
import time
import json
from typing import Optional
from fastapi import APIRouter, Request, Response, Depends, HTTPException
from fastapi.responses import StreamingResponse
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..config import settings
from ..middleware.auth import get_api_key
from ..middleware.rate_limit import check_rate_limit
from ..services.key_service import APIKeyService
from ..services.usage_service import UsageService
from ..services.user_service import UserService
from ..models.api_key import APIKey


router = APIRouter(tags=["Proxy"])


# HTTP client for proxying
http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(settings.upstream_timeout, connect=10.0),
    follow_redirects=True,
)


async def extract_model_from_request(request: Request) -> Optional[str]:
    """Extract model name from request body."""
    try:
        body = await request.body()
        if body:
            data = json.loads(body)
            return data.get("model")
    except:
        pass
    return None


async def extract_usage_from_response(response_data: dict) -> tuple[int, int]:
    """Extract token usage from response."""
    usage = response_data.get("usage", {})
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    return prompt_tokens, completion_tokens


@router.api_route(
    "/v1/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
)
async def proxy_v1(
    request: Request,
    path: str,
    api_key: APIKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Proxy requests to upstream /v1/* endpoints."""
    return await proxy_request(request, f"/v1/{path}", api_key, db)


@router.api_route(
    "/api/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
)
async def proxy_api(
    request: Request,
    path: str,
    api_key: APIKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Proxy requests to upstream /api/* endpoints."""
    return await proxy_request(request, f"/api/{path}", api_key, db)


async def proxy_request(
    request: Request,
    path: str,
    api_key: APIKey,
    db: AsyncSession,
) -> Response:
    """Core proxy logic."""
    start_time = time.time()

    # Rate limiting
    await check_rate_limit(
        request,
        key=f"api_key:{api_key.id}",
        max_requests=api_key.rate_limit,
        window=60,
    )

    # Check quota
    key_service = APIKeyService(db)
    user_service = UserService(db)
    usage_service = UsageService(db)

    # Check key quota
    key_has_quota, key_used, key_limit = await key_service.check_quota(api_key.id)
    if key_limit is not None and not key_has_quota:
        raise HTTPException(
            status_code=429,
            detail="API key quota exceeded",
        )

    # Check user quota
    user_has_quota, user_used, user_limit = await user_service.check_quota(api_key.user_id)
    if not user_has_quota:
        raise HTTPException(
            status_code=429,
            detail="User quota exceeded",
        )

    # Get request body and model
    body = await request.body()
    model = None
    if body:
        try:
            data = json.loads(body)
            model = data.get("model")
        except:
            pass

    # Check model access
    if model:
        has_access = await key_service.check_model_access(api_key.id, model)
        if not has_access:
            raise HTTPException(
                status_code=403,
                detail=f"API key does not have access to model: {model}",
            )

    # Build upstream URL
    upstream_url = f"{settings.upstream_url}{path}"
    if request.url.query:
        upstream_url += f"?{request.url.query}"

    # Prepare headers (remove host, add upstream auth if needed)
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)
    # Remove original authorization to replace with upstream key
    headers.pop("authorization", None)
    headers.pop("Authorization", None)

    # Replace with upstream API key if configured
    if settings.upstream_api_key:
        headers["Authorization"] = f"Bearer {settings.upstream_api_key}"

    # Check if streaming
    is_streaming = False
    if body:
        try:
            data = json.loads(body)
            is_streaming = data.get("stream", False)
        except:
            pass

    try:
        if is_streaming:
            return await handle_streaming_request(
                request, upstream_url, headers, body, api_key, model,
                start_time, db, usage_service, key_service
            )
        else:
            return await handle_normal_request(
                request, upstream_url, headers, body, api_key, model,
                start_time, db, usage_service, key_service
            )
    except httpx.TimeoutException:
        # Record error
        await usage_service.record_usage(
            user_id=api_key.user_id,
            api_key_id=api_key.id,
            endpoint=path,
            method=request.method,
            model=model,
            status_code=504,
            response_time_ms=int((time.time() - start_time) * 1000),
            is_success=False,
            error_message="Upstream timeout",
        )
        raise HTTPException(status_code=504, detail="Upstream timeout")
    except httpx.RequestError as e:
        # Record error
        await usage_service.record_usage(
            user_id=api_key.user_id,
            api_key_id=api_key.id,
            endpoint=path,
            method=request.method,
            model=model,
            status_code=502,
            response_time_ms=int((time.time() - start_time) * 1000),
            is_success=False,
            error_message=str(e),
        )
        raise HTTPException(status_code=502, detail=f"Upstream error: {str(e)}")


async def handle_normal_request(
    request: Request,
    upstream_url: str,
    headers: dict,
    body: bytes,
    api_key: APIKey,
    model: Optional[str],
    start_time: float,
    db: AsyncSession,
    usage_service: UsageService,
    key_service: APIKeyService,
) -> Response:
    """Handle non-streaming request."""
    response = await http_client.request(
        method=request.method,
        url=upstream_url,
        headers=headers,
        content=body,
    )

    response_time_ms = int((time.time() - start_time) * 1000)

    # Try to extract usage from response
    prompt_tokens = 0
    completion_tokens = 0
    try:
        response_data = response.json()
        prompt_tokens, completion_tokens = await extract_usage_from_response(response_data)
    except:
        pass

    # Calculate cost (simple estimation)
    cost = (prompt_tokens + completion_tokens) / 1000 * 0.001  # Simple cost model

    # Record usage
    await usage_service.record_usage(
        user_id=api_key.user_id,
        api_key_id=api_key.id,
        endpoint=upstream_url.replace(settings.upstream_url, ""),
        method=request.method,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost=cost,
        status_code=response.status_code,
        response_time_ms=response_time_ms,
        is_streaming=False,
        is_success=response.status_code < 400,
    )

    # Update key usage
    await key_service.increment_usage(
        api_key.id,
        tokens=prompt_tokens + completion_tokens,
        cost=cost,
    )

    # Build response
    response_headers = dict(response.headers)
    response_headers.pop("content-length", None)
    response_headers.pop("content-encoding", None)
    response_headers.pop("transfer-encoding", None)

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=response_headers,
        media_type=response.headers.get("content-type"),
    )


async def handle_streaming_request(
    request: Request,
    upstream_url: str,
    headers: dict,
    body: bytes,
    api_key: APIKey,
    model: Optional[str],
    start_time: float,
    db: AsyncSession,
    usage_service: UsageService,
    key_service: APIKeyService,
) -> StreamingResponse:
    """Handle streaming request."""

    async def stream_generator():
        total_tokens = 0
        try:
            async with http_client.stream(
                method=request.method,
                url=upstream_url,
                headers=headers,
                content=body,
            ) as response:
                async for chunk in response.aiter_bytes():
                    yield chunk
                    # Try to count tokens from SSE data
                    try:
                        text = chunk.decode("utf-8")
                        for line in text.split("\n"):
                            if line.startswith("data: ") and line != "data: [DONE]":
                                data = json.loads(line[6:])
                                if "usage" in data:
                                    total_tokens = data["usage"].get("total_tokens", 0)
                    except:
                        pass

                response_time_ms = int((time.time() - start_time) * 1000)

                # Record usage after stream completes
                cost = total_tokens / 1000 * 0.001
                await usage_service.record_usage(
                    user_id=api_key.user_id,
                    api_key_id=api_key.id,
                    endpoint=upstream_url.replace(settings.upstream_url, ""),
                    method=request.method,
                    model=model,
                    total_tokens=total_tokens,
                    cost=cost,
                    status_code=response.status_code,
                    response_time_ms=response_time_ms,
                    is_streaming=True,
                    is_success=response.status_code < 400,
                )

                await key_service.increment_usage(api_key.id, tokens=total_tokens, cost=cost)

        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            await usage_service.record_usage(
                user_id=api_key.user_id,
                api_key_id=api_key.id,
                endpoint=upstream_url.replace(settings.upstream_url, ""),
                method=request.method,
                model=model,
                status_code=500,
                response_time_ms=response_time_ms,
                is_streaming=True,
                is_success=False,
                error_message=str(e),
            )
            raise

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# Health check endpoint (no auth required)
@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "APIHub-Gateway"}


# Models endpoint
@router.get("/v1/models")
async def list_models(
    request: Request,
    api_key: APIKey = Depends(get_api_key),
):
    """List available models (proxy to upstream)."""
    try:
        # Prepare headers with upstream auth
        headers = {}
        if settings.upstream_api_key:
            headers["Authorization"] = f"Bearer {settings.upstream_api_key}"
        else:
            # Forward original auth if no upstream key configured
            if "authorization" in request.headers:
                headers["Authorization"] = request.headers["authorization"]

        response = await http_client.get(
            f"{settings.upstream_url}/v1/models",
            headers=headers,
        )
        return Response(
            content=response.content,
            status_code=response.status_code,
            media_type=response.headers.get("content-type"),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Upstream error: {str(e)}")
