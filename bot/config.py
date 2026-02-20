"""
Bot configuration.
All configuration values are loaded from environment variables.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ==================== Bot Configuration ====================
TOKEN = os.getenv("BOT_TOKEN", "8292006040:AAFfkffvG4dxFEQAsQkiBLLXkGR97Cjm5qs")
RUN_MODE = os.getenv("RUN_MODE", "polling").strip().lower()


def _to_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8080"))
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "")
WEBHOOK_SECRET_TOKEN = os.getenv("WEBHOOK_SECRET_TOKEN", "")
WEBHOOK_DROP_PENDING_UPDATES = _to_bool(os.getenv("WEBHOOK_DROP_PENDING_UPDATES", "true"), default=True)

CHANNEL_ID = os.getenv("CHANNEL_ID", "route_net")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "route_net")
ADMIN_IDS = [os.getenv("ADMIN_ID", "6245412936")]

# ==================== Payment Configuration ====================
CARD_NUMBER = os.getenv("CARD_NUMBER", "1234-5678-9012-3456")
CARD_HOLDER = os.getenv("CARD_HOLDER", "نام صاحب کارت")

# ==================== MikroTik Configuration ====================
# MikroTik RouterOS connection details for WireGuard management
MIKROTIK_HOST = os.getenv("MIKROTIK_HOST", "192.168.1.1")
MIKROTIK_USER = os.getenv("MIKROTIK_USER", "admin")
MIKROTIK_PASS = os.getenv("MIKROTIK_PASS", "password")
MIKROTIK_PORT = int(os.getenv("MIKROTIK_PORT", "22"))

# ==================== WireGuard Server Configuration ====================
WG_INTERFACE = os.getenv("WIREGUARD_INTERFACE_NAME", "wg-user")
WG_SERVER_PUBLIC_KEY = os.getenv("WIREGUARD_PUBLIC_KEY", "")
WG_SERVER_ENDPOINT = os.getenv("WIREGUARD_SERVER_ENDPOINT", "")
WG_SERVER_PORT = int(os.getenv("WIREGUARD_SERVER_PORT", "51820"))

# IP range for client addresses (e.g., 192.168.30.0/24)
ip_range = os.getenv("WIREGUARD_IP_RANGE", "192.168.30.0/24").split('/')[0]
WG_CLIENT_NETWORK_BASE = ip_range.rsplit('.', 1)[0] + ".0"  # e.g., 192.168.30.0

WG_CLIENT_DNS = os.getenv("WIREGUARD_DNS", "8.8.8.8,1.0.0.1")

# ==================== Admin States (In-Memory) ====================
# These are temporary states stored in memory for admin operations
admin_plan_state = {}  # For plan creation/editing flow
admin_create_account_state = {}  # For custom account creation flow
user_payment_state = {}  # For user payment flow
admin_user_search_state = {}  # For admin user search flow
admin_wallet_adjust_state = {}  # For admin wallet increase/decrease flow
admin_discount_state = {}  # For admin discount code creation flow
admin_receipt_reject_state = {}  # For admin reject-reason flow
admin_service_type_state = {}  # For service type management flow
admin_server_state = {}  # For server management flow
admin_tutorial_state = {}  # For tutorial creation flow
