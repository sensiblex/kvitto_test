import pytest

from app.services.payments import (
    InvalidInstallmentError,
    InvalidPromoCodeError,
    InvalidStatusTransitionError,
    PaymentMethod,
    PaymentStatus,
    build_payment_schedule,
    calculate_discount,
    calculate_installment_schedule,
    calculate_payment_amount,
    can_transition_status,
    validate_promo_code,
    validate_status_transition,
)


@pytest.mark.parametrize(
    ("price", "promo_code", "expected"),
    [
        (1_990_000, None, (1_990_000, 0)),
        (1_990_000, "KVITTO10", (1_791_000, 199_000)),
        (1_990_000, "kvitto10", (1_791_000, 199_000)),
        (1_990_000, "Kvitto10", (1_791_000, 199_000)),
        (1_990_000, "KvItTo10", (1_791_000, 199_000)),
    ],
)
def test_calculate_payment_amount(price, promo_code, expected):
    assert calculate_payment_amount(price, promo_code) == expected


@pytest.mark.parametrize("promo_code", ["UNKNOWN", "KVITTO", ""])
def test_invalid_promo_code_raises(promo_code):
    with pytest.raises(InvalidPromoCodeError):
        calculate_discount(1_990_000, promo_code)


@pytest.mark.parametrize("promo_code", [None, "KVITTO10", "kvitto10"])
def test_validate_promo_code_accepts_supported_values(promo_code):
    assert validate_promo_code(promo_code) is None


@pytest.mark.parametrize("promo_code", ["UNKNOWN", ""])
def test_validate_promo_code_rejects_unknown_values(promo_code):
    with pytest.raises(InvalidPromoCodeError):
        validate_promo_code(promo_code)


@pytest.mark.parametrize(
    ("months", "expected"),
    [
        (3, [663_334, 663_333, 663_333]),
        (6, [331_667, 331_667, 331_667, 331_667, 331_666, 331_666]),
        (
            12,
            [165_834, 165_834, 165_834, 165_834] + [165_833] * 8,
        ),
    ],
)
def test_installment_schedule(months, expected):
    schedule = calculate_installment_schedule(1_990_000, months)

    assert schedule == expected
    assert sum(schedule) == 1_990_000


@pytest.mark.parametrize("months", [3, 6, 12])
@pytest.mark.parametrize("amount", [990_000, 1_990_000, 2_990_000, 100])
def test_installment_schedule_sum_equals_amount(amount, months):
    schedule = calculate_installment_schedule(amount, months)

    assert sum(schedule) == amount
    assert len(schedule) == months


def test_installment_schedule_distributes_remainder_to_first_payments():
    schedule = calculate_installment_schedule(100, 3)

    assert schedule == [34, 33, 33]
    assert sum(schedule) == 100


@pytest.mark.parametrize("months", [1, 4, 24])
def test_installment_schedule_rejects_unsupported_period(months):
    with pytest.raises(InvalidInstallmentError):
        calculate_installment_schedule(1_990_000, months)


def test_installment_schedule_rejects_negative_amount():
    with pytest.raises(InvalidInstallmentError):
        calculate_installment_schedule(-1, 3)


def test_build_installment_schedule_requires_months():
    with pytest.raises(InvalidInstallmentError):
        build_payment_schedule(1_990_000, PaymentMethod.INSTALLMENT)


def test_build_non_installment_schedule_rejects_months():
    with pytest.raises(InvalidInstallmentError):
        build_payment_schedule(1_990_000, PaymentMethod.CARD, 3)


@pytest.mark.parametrize("method", [PaymentMethod.CARD, PaymentMethod.SBP])
def test_build_non_installment_schedule_returns_none(method):
    assert build_payment_schedule(1_990_000, method) is None


@pytest.mark.parametrize(
    ("current_status", "new_status"),
    [
        (PaymentStatus.PENDING, PaymentStatus.SUCCEEDED),
        (PaymentStatus.PENDING, PaymentStatus.FAILED),
        (PaymentStatus.SUCCEEDED, PaymentStatus.REFUNDED),
    ],
)
def test_valid_status_transitions(current_status, new_status):
    assert can_transition_status(current_status, new_status)
    validate_status_transition(current_status, new_status)


@pytest.mark.parametrize(
    ("current_status", "new_status"),
    [
        (PaymentStatus.PENDING, PaymentStatus.PENDING),
        (PaymentStatus.PENDING, PaymentStatus.REFUNDED),
        (PaymentStatus.SUCCEEDED, PaymentStatus.PENDING),
        (PaymentStatus.FAILED, PaymentStatus.SUCCEEDED),
        (PaymentStatus.REFUNDED, PaymentStatus.SUCCEEDED),
    ],
)
def test_invalid_status_transitions(current_status, new_status):
    assert not can_transition_status(current_status, new_status)
    with pytest.raises(InvalidStatusTransitionError):
        validate_status_transition(current_status, new_status)
