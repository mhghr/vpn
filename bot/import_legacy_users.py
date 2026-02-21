"""Import users from a legacy CSV export into the current bot database.

Expected CSV layout (Excel-style columns):
- Column B: user Telegram ID
- Column C: first name
- Column D: username

Example:
    python import_legacy_users.py --csv users.csv
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from database import SessionLocal
from models import User


def normalize_username(value: str) -> str | None:
    if value is None:
        return None
    username = value.strip()
    if not username:
        return None
    return username[1:] if username.startswith("@") else username


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import legacy users from CSV (B=telegram_id, C=first_name, D=username)."
    )
    parser.add_argument(
        "--csv",
        default="users.csv",
        help="Path to input CSV file. Default: users.csv",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate input without writing to database.",
    )
    return parser.parse_args()


def extract_user_fields(row: list[str], row_number: int) -> tuple[str, str, str | None] | None:
    if len(row) < 4:
        return None

    telegram_id = (row[1] or "").strip()
    first_name = (row[2] or "").strip()
    username = normalize_username(row[3] or "")

    if not telegram_id or not first_name:
        return None

    return telegram_id, first_name, username


def run_import(csv_path: Path, dry_run: bool = False) -> None:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    created = 0
    updated = 0
    skipped = 0

    db = SessionLocal()
    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.reader(csv_file)
            for row_number, row in enumerate(reader, start=1):
                parsed = extract_user_fields(row, row_number)
                if not parsed:
                    skipped += 1
                    continue

                telegram_id, first_name, username = parsed
                existing = db.query(User).filter(User.telegram_id == telegram_id).first()

                if existing:
                    changed = False
                    if existing.first_name != first_name:
                        existing.first_name = first_name
                        changed = True
                    if existing.username != username:
                        existing.username = username
                        changed = True
                    if changed:
                        updated += 1
                else:
                    db.add(
                        User(
                            telegram_id=telegram_id,
                            first_name=first_name,
                            username=username,
                        )
                    )
                    created += 1

        if dry_run:
            db.rollback()
        else:
            db.commit()

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    mode = "DRY-RUN" if dry_run else "IMPORT"
    print(
        f"[{mode}] Done. Created: {created}, Updated: {updated}, Skipped: {skipped}, File: {csv_path}"
    )


def main() -> None:
    args = parse_args()
    run_import(Path(args.csv), dry_run=args.dry_run)


if __name__ == "__main__":
    main()
