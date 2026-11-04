"""
app_utils.py — Application utility functions
"""

def compute_tax(amount: float, rate: float) -> float:
    """Calculate tax amount given a base amount and rate percentage."""
    return amount * (rate / 100)


def format_currency(amount: float, symbol: str = "$") -> str:
    return f"{symbol}{amount:.2f}"
