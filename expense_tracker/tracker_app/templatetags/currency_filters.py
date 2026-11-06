"""
Custom template filters for currency formatting.
"""
from django import template
from decimal import Decimal, InvalidOperation

register = template.Library()


@register.filter
def currency(value):
    """
    Format currency without decimal places.
    Usage: {{ amount|currency }} -> "1.000.000 đ"
    """
    if value is None:
        return "0 đ"
    
    try:
        # Convert to Decimal if it's not already
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
        
        # Round to nearest integer (remove decimals)
        value = value.quantize(Decimal('1'))
        
        # Format with Vietnamese thousand separator
        formatted = '{:,.0f}'.format(value).replace(',', '.')
        return f"{formatted} đ"
    except (InvalidOperation, ValueError, TypeError):
        return "0 đ"


@register.filter
def currency_raw(value):
    """
    Format currency without decimal places and without currency symbol.
    Usage: {{ amount|currency_raw }} -> "1.000.000"
    """
    if value is None:
        return "0"
    
    try:
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
        
        value = value.quantize(Decimal('1'))
        return '{:,.0f}'.format(value).replace(',', '.')
    except (InvalidOperation, ValueError, TypeError):
        return "0"


@register.filter
def currency_compact(value):
    """
    Format currency in compact form (K, M, B).
    Usage: {{ amount|currency_compact }} -> "1.000.000 đ" or "1,5M đ"
    """
    if value is None:
        return "0 đ"
    
    try:
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
        
        value = float(value.quantize(Decimal('1')))
        
        if value >= 1_000_000_000:
            return f"{value / 1_000_000_000:,.1f}B đ".replace(',', '.')
        elif value >= 1_000_000:
            return f"{value / 1_000_000:,.1f}M đ".replace(',', '.')
        elif value >= 1_000:
            return f"{value / 1_000:,.1f}K đ".replace(',', '.')
        else:
            return f"{value:,.0f} đ".replace(',', '.')
    except (InvalidOperation, ValueError, TypeError):
        return "0 đ"