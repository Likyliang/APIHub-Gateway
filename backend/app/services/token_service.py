"""
Token Service - Manage user token balance and transactions
"""
from typing import Optional, List, Tuple
from datetime import datetime, timezone
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.user import User, TokenTransaction


class TokenService:
    """Service for token/balance management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_balance(self, user_id: int) -> float:
        """Get user's current token balance."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        return user.token_balance if user else 0.0

    async def recharge(
        self,
        user_id: int,
        amount: float,
        order_no: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Tuple[bool, float, Optional[TokenTransaction]]:
        """
        Add tokens to user's balance.
        Returns (success, new_balance, transaction)
        """
        if amount <= 0:
            return False, 0.0, None

        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return False, 0.0, None

        balance_before = user.token_balance
        user.token_balance += amount
        user.total_recharged += amount

        # Create transaction record
        transaction = TokenTransaction(
            user_id=user_id,
            amount=amount,
            balance_before=balance_before,
            balance_after=user.token_balance,
            transaction_type="recharge",
            description=description or f"充值 {amount} 代币",
            order_no=order_no,
        )
        self.db.add(transaction)
        await self.db.flush()

        return True, user.token_balance, transaction

    async def consume(
        self,
        user_id: int,
        amount: float,
        api_key_id: Optional[int] = None,
        description: Optional[str] = None,
        apply_discount: bool = True,
    ) -> Tuple[bool, float, Optional[TokenTransaction]]:
        """
        Deduct tokens from user's balance.
        Returns (success, new_balance, transaction)
        """
        if amount <= 0:
            return False, 0.0, None

        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return False, 0.0, None

        # Apply user discount
        actual_amount = amount
        if apply_discount and user.discount_rate < 1.0:
            actual_amount = amount * user.discount_rate

        # Check balance
        if user.token_balance < actual_amount:
            return False, user.token_balance, None

        balance_before = user.token_balance
        user.token_balance -= actual_amount
        user.total_consumed += actual_amount

        # Create transaction record
        transaction = TokenTransaction(
            user_id=user_id,
            amount=-actual_amount,
            balance_before=balance_before,
            balance_after=user.token_balance,
            transaction_type="consume",
            description=description or f"消费 {actual_amount:.4f} 代币",
            api_key_id=api_key_id,
        )
        self.db.add(transaction)
        await self.db.flush()

        return True, user.token_balance, transaction

    async def check_balance(self, user_id: int, amount: float) -> Tuple[bool, float]:
        """
        Check if user has enough balance.
        Returns (has_enough, current_balance)
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return False, 0.0

        # Apply discount to check
        actual_amount = amount
        if user.discount_rate < 1.0:
            actual_amount = amount * user.discount_rate

        return user.token_balance >= actual_amount, user.token_balance

    async def refund(
        self,
        user_id: int,
        amount: float,
        order_no: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Tuple[bool, float, Optional[TokenTransaction]]:
        """
        Refund tokens to user's balance.
        Returns (success, new_balance, transaction)
        """
        if amount <= 0:
            return False, 0.0, None

        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return False, 0.0, None

        balance_before = user.token_balance
        user.token_balance += amount

        transaction = TokenTransaction(
            user_id=user_id,
            amount=amount,
            balance_before=balance_before,
            balance_after=user.token_balance,
            transaction_type="refund",
            description=description or f"退款 {amount} 代币",
            order_no=order_no,
        )
        self.db.add(transaction)
        await self.db.flush()

        return True, user.token_balance, transaction

    async def adjust(
        self,
        user_id: int,
        amount: float,
        description: Optional[str] = None,
    ) -> Tuple[bool, float, Optional[TokenTransaction]]:
        """
        Adjust user's balance (admin operation).
        Positive = add, Negative = deduct
        Returns (success, new_balance, transaction)
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return False, 0.0, None

        balance_before = user.token_balance
        new_balance = balance_before + amount

        # Don't allow negative balance
        if new_balance < 0:
            return False, balance_before, None

        user.token_balance = new_balance

        transaction = TokenTransaction(
            user_id=user_id,
            amount=amount,
            balance_before=balance_before,
            balance_after=new_balance,
            transaction_type="adjust",
            description=description or f"余额调整 {amount:+.2f}",
        )
        self.db.add(transaction)
        await self.db.flush()

        return True, new_balance, transaction

    async def get_transactions(
        self,
        user_id: int,
        transaction_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[TokenTransaction]:
        """Get user's transaction history."""
        query = select(TokenTransaction).where(TokenTransaction.user_id == user_id)

        if transaction_type:
            query = query.where(TokenTransaction.transaction_type == transaction_type)

        query = query.order_by(desc(TokenTransaction.created_at)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_user_stats(self, user_id: int) -> dict:
        """Get user's token statistics."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            return {}

        return {
            "balance": user.token_balance,
            "total_recharged": user.total_recharged,
            "total_consumed": user.total_consumed,
            "discount_rate": user.discount_rate,
            "discount_percent": int((1 - user.discount_rate) * 100) if user.discount_rate < 1 else 0,
        }

    async def set_discount(self, user_id: int, discount_rate: float) -> bool:
        """Set user's discount rate (0 < rate <= 1)."""
        if discount_rate <= 0 or discount_rate > 1:
            return False

        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return False

        user.discount_rate = discount_rate
        return True
