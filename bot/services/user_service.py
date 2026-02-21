from models import User, WireGuardConfig
from config import ADMIN_IDS


def get_or_create_user(db, telegram_id: str, username=None, first_name=None, last_name=None):
    user = db.query(User).filter(User.telegram_id == str(telegram_id)).first()
    if not user:
        admin = str(telegram_id) in ADMIN_IDS
        user = User(
            telegram_id=str(telegram_id),
            username=username,
            first_name=first_name,
            last_name=last_name,
            is_member=False,
            is_admin=admin,
            wallet_balance=0,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def get_user(db, telegram_id: str):
    return db.query(User).filter(User.telegram_id == str(telegram_id)).first()


def is_admin(telegram_id: str) -> bool:
    return str(telegram_id) in ADMIN_IDS


def calculate_org_user_financials(db, user_obj: User):
    active_configs = db.query(WireGuardConfig).filter(
        WireGuardConfig.user_telegram_id == user_obj.telegram_id,
        WireGuardConfig.status == "active",
    ).all()
    total_traffic_bytes = sum((cfg.cumulative_rx_bytes or 0) + (cfg.cumulative_tx_bytes or 0) for cfg in active_configs)
    total_traffic_gb = total_traffic_bytes / (1024 ** 3)
    price_per_gb = user_obj.org_price_per_gb or 0
    debt_amount = int(total_traffic_gb * price_per_gb)
    return {
        "active_configs": active_configs,
        "total_traffic_gb": total_traffic_gb,
        "price_per_gb": price_per_gb,
        "debt_amount": debt_amount,
    }
