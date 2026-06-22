def format_currency(value, symbol="₱"):
    if value is None:
        return ""
    return f"{symbol} {value:,.2f}"

def format_percent(value):
    if value is None:
        return ""
    return f"{value * 100:.2f}%"
