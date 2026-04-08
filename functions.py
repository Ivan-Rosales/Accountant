from decimal import Decimal, ROUND_HALF_UP


def get_icon(icon):
    return f'assets/icons/{icon}.png'


def decimal_property(func):
    def wrapper_func(*args, **kwargs):
        return normalize_number(Decimal(func(*args, **kwargs)))

    return wrapper_func


def normalize_number(number, rounding=ROUND_HALF_UP):
    if not isinstance(number, Decimal):
        number = Decimal(number)

    return number.quantize(Decimal('0.01'), rounding=rounding)