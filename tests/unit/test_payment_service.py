import logging

import pytest

from tlvflow.domain.payment_service import PaymentProcessingError, PaymentService


@pytest.fixture()
def service() -> PaymentService:
    return PaymentService()


@pytest.fixture()
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[float]]:
    """Patch asyncio.sleep so tests run instantly, and track delays."""
    import asyncio

    calls: dict[str, list[float]] = {"delays": []}

    async def fake_sleep(delay: float) -> None:
        calls["delays"].append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    return calls


# -------------------------
# Success paths
# -------------------------


@pytest.mark.asyncio
async def test_process_charge_success(
    service: PaymentService, no_sleep, caplog
) -> None:
    caplog.set_level(logging.INFO)

    result = await service.process_charge("ride-123", 15.0, "pm_tok_abc")

    assert result is True
    assert no_sleep["delays"] == [0.5]
    assert "Processing charge of" in caplog.text
    assert "Successfully charged" in caplog.text


@pytest.mark.asyncio
async def test_issue_receipt_success(service: PaymentService, no_sleep, caplog) -> None:
    caplog.set_level(logging.INFO)

    result = await service.issue_receipt(
        "ride-123", 15.0, "user@example.com", "pm_tok_abc"
    )

    assert result is True
    assert no_sleep["delays"] == [0.2]
    assert "Issuing receipt of" in caplog.text
    assert "Successfully issued receipt" in caplog.text


@pytest.mark.asyncio
async def test_issue_refund_success(service: PaymentService, no_sleep, caplog) -> None:
    caplog.set_level(logging.INFO)

    result = await service.issue_refund(
        "ride-123", 10.0, "user@example.com", "pm_tok_abc"
    )

    assert result is True
    assert no_sleep["delays"] == [0.5]
    assert "Processing refund of" in caplog.text
    assert "Successfully refunded" in caplog.text


# -------------------------
# Common validation (_validate_common)
# -------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_ride_id", ["", "   "])
async def test_validate_common_invalid_ride_id_raises(
    service: PaymentService, no_sleep, bad_ride_id: str
) -> None:
    with pytest.raises(
        PaymentProcessingError, match=r"ride_id must be a non-empty string\."
    ):
        await service.process_charge(bad_ride_id, 15.0, "pm_tok_abc")

    assert no_sleep["delays"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_payment_method_id", ["", "   "])
async def test_validate_common_invalid_payment_method_id_raises(
    service: PaymentService, no_sleep, bad_payment_method_id: str
) -> None:
    with pytest.raises(
        PaymentProcessingError,
        match=r"payment_method_id must be a non-empty string\.",
    ):
        await service.process_charge("ride-123", 15.0, bad_payment_method_id)

    assert no_sleep["delays"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_amount", [0, 0.0, -1, -10.5])
async def test_validate_common_invalid_amount_raises_on_all_methods(
    service: PaymentService, no_sleep, bad_amount: float
) -> None:
    with pytest.raises(
        PaymentProcessingError, match=r"Amount must be greater than zero\."
    ):
        await service.process_charge("ride-123", float(bad_amount), "pm_tok_abc")

    with pytest.raises(
        PaymentProcessingError, match=r"Amount must be greater than zero\."
    ):
        await service.issue_receipt(
            "ride-123", float(bad_amount), "user@example.com", "pm_tok_abc"
        )

    with pytest.raises(
        PaymentProcessingError, match=r"Amount must be greater than zero\."
    ):
        await service.issue_refund(
            "ride-123", float(bad_amount), "user@example.com", "pm_tok_abc"
        )

    assert no_sleep["delays"] == []


# -------------------------
# Email validation (only: not email OR "@" not in email)
# -------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_email", ["", "   ", "just-a-string", "domain.com"])
async def test_issue_receipt_invalid_email_raises(
    service: PaymentService, no_sleep, bad_email: str
) -> None:
    with pytest.raises(
        PaymentProcessingError, match=r"email must be a valid email address\."
    ):
        await service.issue_receipt("ride-123", 15.0, bad_email, "pm_tok_abc")

    assert no_sleep["delays"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_email", ["", "   ", "just-a-string", "domain.com"])
async def test_issue_refund_invalid_email_raises(
    service: PaymentService, no_sleep, bad_email: str
) -> None:
    with pytest.raises(
        PaymentProcessingError, match=r"email must be a valid email address\."
    ):
        await service.issue_refund("ride-123", 15.0, bad_email, "pm_tok_abc")

    assert no_sleep["delays"] == []
