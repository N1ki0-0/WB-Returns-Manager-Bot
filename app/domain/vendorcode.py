import re

_SUFFIX_RE = re.compile(r"^(.*)\s\((\d+)\)$")

def next_vendor_code(base: str, existing: set[str]) -> str:
    """
    base: исходный vendorCode
    existing: множество уже существующих vendorCode (можно получить через cards/list по textSearch=base)
    """
    # Считаем, что base без суффикса (если с суффиксом — тоже обработаем)
    m = _SUFFIX_RE.match(base.strip())
    if m:
        base_root = m.group(1).strip()
    else:
        base_root = base.strip()

    # Если base_root свободен и его нет в existing — можно использовать base_root (но вы хотите именно (1)+)
    # По требованию: всегда добавлять (1) и дальше
    n = 1
    while True:
        cand = f"{base_root} ({n})"
        if cand not in existing:
            return cand
        n += 1
