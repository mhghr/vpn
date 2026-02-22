import os
CARD_INFO_FILE = "card_info.txt"


def get_card_info() -> tuple[str, str]:
    if os.path.exists(CARD_INFO_FILE):
        try:
            with open(CARD_INFO_FILE, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines()]
            number = lines[0] if len(lines) > 0 else ""
            holder = lines[1] if len(lines) > 1 else ""
            return number, holder
        except Exception:
            pass
    return "", ""


def set_card_info(card_number: str, card_holder: str = "") -> None:
    with open(CARD_INFO_FILE, "w", encoding="utf-8") as f:
        f.write((card_number or "").strip() + "\n")
        f.write((card_holder or "").strip() + "\n")
