from django import template

register = template.Library()


@register.filter
def get_item(value, key):
    if value is None:
        return ""

    try:
        if isinstance(value, list):
            return value[int(key)]
        return value.get(key, "")
    except (AttributeError, IndexError, TypeError, ValueError):
        return ""


@register.filter
def split(value, separator=","):
    return str(value or "").split(separator)


@register.filter
def fix_encoding(value):
    """Corrige dupla codificacao UTF-8 herdada de importacoes legadas."""
    if not isinstance(value, str):
        return value
    try:
        return value.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return value


@register.filter
def ordinal(value):
    """Retorna sufixo ordinal para numeros (2 → 2ª, 3 → 3ª...)."""
    try:
        n = int(value)
        return f"{n}ª"
    except (TypeError, ValueError):
        return value
