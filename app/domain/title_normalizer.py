import re

_COLOR_MAP = {
    "black": "black",
    "blue": "blue",
    "white": "white",
    "green": "green",
    "purple": "purple",
    "violet": "purple",
    "grey": "grey",
    "gray": "grey",
    "yellow": "yellow",
    "red": "red",
    # RU варианты (если вдруг встречаются)
    "чер": "black", "чер.": "black", "черный": "black", "чёрный": "black",
    "син": "blue", "син.": "blue", "синий": "blue",
    "бел": "white", "бел.": "white", "белый": "white",
    "зел": "green", "зел.": "green", "зеленый": "green",
    "фиол": "purple", "фиол.": "purple", "фиолетовый": "purple",
}

_MODEL_PATTERNS = [
    # Samsung Axx / Cxx и т.п.
    re.compile(r"\b([ac]\d{2})\b", re.IGNORECASE),      # A25, C85
    re.compile(r"\b(a\d{2}c)\b", re.IGNORECASE),        # A15C
    # Redmi / просто "12", "13"
    re.compile(r"\b(note\s*\d+)\b", re.IGNORECASE),     # Note 13
    re.compile(r"\b(\d{2})\b"),                         # 12, 13, 15
]

def _extract_color(title: str) -> str | None:
    t = title.strip().lower().replace("—", " ").replace("-", " ")
    tokens = [x.strip(" .,/()[]") for x in t.split() if x.strip(" .,/()[]")]
    # Ищем цвет в хвосте (обычно в конце)
    for tok in reversed(tokens[-5:]):
        if tok in _COLOR_MAP:
            return _COLOR_MAP[tok]
        # иногда "Black" + "чер." — берём english
        if tok.lower() in _COLOR_MAP:
            return _COLOR_MAP[tok.lower()]
    return None

def _extract_model(title: str) -> str | None:
    t = title.strip().lower()
    # подчистим шум, чтобы "Galaxy" и объёмы не мешали
    t = re.sub(r"\b(смартфон|samsung|galaxy|redmi|xiaomi|iphone|gb|гб|5g|4g)\b", " ", t, flags=re.IGNORECASE)
    t = re.sub(r"\s+", " ", t).strip()

    for pat in _MODEL_PATTERNS:
        m = pat.search(t)
        if m:
            model = m.group(1).strip().upper().replace("NOTE", "Note")
            # привести "Note 13" к "13" или "Note13"? (вы хотели просто "13 blue")
            model = model.replace("NOTE ", "").replace("Note ", "")
            return model
    return None

def normalize_phone_title(title: str) -> str:
    """
    Возвращает короткий ярлык типа: 'A25 black' / '12 blue' / 'C85 black'.
    """
    model = _extract_model(title) or "UNKNOWN"
    color = _extract_color(title) or ""
    if color:
        return f"{model} {color}"
    return model
