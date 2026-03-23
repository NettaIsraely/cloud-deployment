import asyncio
import logging

logger = logging.getLogger(__name__)


class PaymentProcessingError(Exception):
    """Raised when a mocked payment operation fails validation."""


class PaymentService:
    """Service responsible for handling mocked payment operations."""

    @staticmethod
    def _validate_common(ride_id: str, amount: float, payment_method_id: str) -> None:
        if not ride_id or not ride_id.strip():
            raise PaymentProcessingError("ride_id must be a non-empty string.")
        if not payment_method_id or not payment_method_id.strip():
            raise PaymentProcessingError(
                "payment_method_id must be a non-empty string."
            )
        if amount <= 0:
            raise PaymentProcessingError("Amount must be greater than zero.")

    async def process_charge(
        self,
        ride_id: str,
        amount: float,
        payment_method_id: str,
    ) -> bool:
        """Process a mocked charge for a completed ride."""
        self._validate_common(ride_id, amount, payment_method_id)

        logger.info(
            "Processing charge of %s ILS for ride %s using token %s...",
            amount,
            ride_id,
            payment_method_id,
        )

        await asyncio.sleep(0.5)

        logger.info("Successfully charged %s ILS for ride %s.", amount, ride_id)
        return True

    async def issue_receipt(
        self,
        ride_id: str,
        amount: float,
        email: str,
        payment_method_id: str,
    ) -> bool:
        """Issue a mocked receipt to the user's email."""
        self._validate_common(ride_id, amount, payment_method_id)
        if not email or "@" not in email:
            raise PaymentProcessingError("email must be a valid email address.")

        logger.info(
            "Issuing receipt of %s ILS for ride %s to %s...",
            amount,
            ride_id,
            email,
        )

        await asyncio.sleep(0.2)

        logger.info("Successfully issued receipt for ride %s.", ride_id)
        return True

    async def issue_refund(
        self,
        ride_id: str,
        amount: float,
        email: str,
        payment_method_id: str,
    ) -> bool:
        """Process a mocked refund for a ride."""
        self._validate_common(ride_id, amount, payment_method_id)
        if not email or "@" not in email:
            raise PaymentProcessingError("email must be a valid email address.")

        logger.info(
            "Processing refund of %s ILS for ride %s to token %s...",
            amount,
            ride_id,
            payment_method_id,
        )

        await asyncio.sleep(0.5)

        logger.info(
            "Successfully refunded %s ILS for ride %s. Notification sent to %s.",
            amount,
            ride_id,
            email,
        )
        return True
