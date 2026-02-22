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


# ==================== Representative Bot Configuration ====================
AGENT_BOT_DOCKER_IMAGE = os.getenv("AGENT_BOT_DOCKER_IMAGE", "vpn-agent-bot:latest")
AGENT_BOT_CONTAINER_PREFIX = os.getenv("AGENT_BOT_CONTAINER_PREFIX", "vpn_agent")
AGENT_BOT_DOCKER_NETWORK = os.getenv("AGENT_BOT_DOCKER_NETWORK", "")

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

admin_representative_state = {}  # For representative management flow

admin_card_state = {}  # For admin card-number edit flow
org_user_state = {}  # For organization-user create-account/settlement flow
