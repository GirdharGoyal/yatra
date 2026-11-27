def calculate_total_amount(unit_price: float, travellers: int) -> float:
    return round(float(unit_price) * int(travellers), 2)


def calculate_refund(amount: float, hours_until_travel: float) -> float:
    # Free cancellation if > 24 hours before travel date; otherwise 50% refund
    if hours_until_travel >= 24.0:
        return round(amount, 2)
    return round(amount * 0.5, 2)
