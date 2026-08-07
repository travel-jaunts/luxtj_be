"""Default currency symbols when metadata is missing."""

DEFAULT_CURRENCY_SYMBOLS: dict[str, str] = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "INR": "₹",
    "JPY": "¥",
    "AED": "د.إ",
    "AUD": "A$",
    "CAD": "C$",
    "CHF": "CHF",
    "SGD": "S$",
    "THB": "฿",
    "MYR": "RM",
    "CNY": "¥",
    "HKD": "HK$",
    "NZD": "NZ$",
    "SAR": "﷼",
    "KRW": "₩",
}


def default_currency_symbol(code: str) -> str | None:
    return DEFAULT_CURRENCY_SYMBOLS.get(code.upper())
