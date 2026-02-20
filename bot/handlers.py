import json
import os
import io
import re
import subprocess
from datetime import datetime
from datetime import datetime, timedelta

from aiogram import Dispatcher
from aiogram.types import Message, CallbackQuery, FSInputFile, BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton

from database import SessionLocal, engine
from models import User, Panel, Plan, PaymentReceipt, WireGuardConfig, GiftCode, ServiceType, Server, PlanServerMap, ServiceTutorial, Representative
from config import (
    CHANNEL_ID, CHANNEL_USERNAME, ADMIN_IDS,
    admin_plan_state, admin_create_account_state, user_payment_state,
    admin_user_search_state, admin_wallet_adjust_state, admin_discount_state, admin_receipt_reject_state,
    admin_service_type_state, admin_server_state, admin_tutorial_state, admin_representative_state,
    CARD_NUMBER, CARD_HOLDER,
    MIKROTIK_HOST, MIKROTIK_USER, MIKROTIK_PASS, MIKROTIK_PORT,
    WG_INTERFACE, WG_SERVER_PUBLIC_KEY, WG_SERVER_ENDPOINT, WG_SERVER_PORT,
    WG_CLIENT_NETWORK_BASE, WG_CLIENT_DNS,
    AGENT_BOT_DOCKER_IMAGE, AGENT_BOT_CONTAINER_PREFIX, AGENT_BOT_DOCKER_NETWORK
)

from keyboards import (
    get_main_keyboard, get_admin_keyboard, get_panels_keyboard,
    get_pending_panel_keyboard, get_plans_keyboard, get_plan_list_keyboard,
    get_plan_action_keyboard, get_plan_edit_keyboard, get_buy_keyboard,
    get_payment_method_keyboard, get_receipt_action_keyboard, get_receipt_done_keyboard, get_create_account_keyboard,
    get_configs_keyboard, get_config_detail_keyboard, get_found_users_keyboard,
    get_admin_user_manage_keyboard, get_payment_method_keyboard_for_renew,
    get_admin_config_detail_keyboard, get_admin_config_confirm_delete_keyboard,
    get_admin_user_configs_keyboard, get_test_account_keyboard, get_service_types_keyboard,
    get_servers_service_type_keyboard, get_servers_keyboard, get_server_action_keyboard,
    get_service_type_picker_keyboard, get_plan_servers_picker_keyboard, get_plan_server_select_keyboard,
    get_representatives_keyboard, get_representative_action_keyboard
)

from texts import (
    WELCOME_MESSAGE, NOT_MEMBER_MESSAGE, ADMIN_MESSAGE, PANELS_MESSAGE, SEARCH_USER_MESSAGE, PLANS_MESSAGE, TEST_ACCOUNT_PLAN_NAME
)


dp = Dispatcher()


# Helper functions
def normalize_numbers(text: str) -> str:
    """Convert Persian/Arabic numbers to English numbers."""
    if not text:
        return text
    # Persian numbers: ۰۱۲۳۴۵۶۷۸۹
    # Arabic numbers: ٠١٢٣٤٥٦٧٨٩
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    arabic_digits = '٠١٢٣٤٥٦٧٨٩'
    english_digits = '0123456789'
    
    result = text
    for i, d in enumerate(persian_digits):
        result = result.replace(d, english_digits[i])
    for i, d in enumerate(arabic_digits):
        result = result.replace(d, english_digits[i])
    
    return result


def load_pending_panel():
    try:
        if os.path.exists("pending_panel.json"):
            with open("pending_panel.json", "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None


def delete_pending_panel():
    try:
        if os.path.exists("pending_panel.json"):
            os.remove("pending_panel.json")
    except Exception:
        pass


async def check_channel_member(bot, user_id: int, channel_id: str) -> bool:
    try:
        from aiogram.enums import ChatMemberStatus
        chat_id = f"@{channel_id}" if not channel_id.startswith("-") else channel_id
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        return member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
    except Exception:
        return False


def get_or_create_user(db, telegram_id: str, username=None, first_name=None, last_name=None):
    user = db.query(User).filter(User.telegram_id == str(telegram_id)).first()
    if not user:
        is_admin = str(telegram_id) in ADMIN_IDS
        user = User(telegram_id=str(telegram_id), username=username, first_name=first_name, last_name=last_name,
                    is_member=False, is_admin=is_admin, wallet_balance=0)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def get_user(db, telegram_id: str):
    return db.query(User).filter(User.telegram_id == str(telegram_id)).first()


def is_admin(telegram_id: str) -> bool:
    return str(telegram_id) in ADMIN_IDS


def _sanitize_container_name(name: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9_-]", "-", name or "agent")
    return base.strip("-").lower() or "agent"


def start_representative_container(rep: Representative) -> tuple[bool, str]:
    container_name = f"{AGENT_BOT_CONTAINER_PREFIX}_{rep.id}_{_sanitize_container_name(rep.name)}"
    env_vars = [
        "-e", f"BOT_TOKEN={rep.bot_token}",
        "-e", f"ADMIN_ID={rep.admin_telegram_id}",
        "-e", f"CHANNEL_ID={rep.channel_id}",
        "-e", f"CHANNEL_USERNAME={rep.channel_id}",
    ]
    cmd = ["docker", "run", "-d", "--restart", "unless-stopped", "--name", container_name]
    if AGENT_BOT_DOCKER_NETWORK:
        cmd += ["--network", AGENT_BOT_DOCKER_NETWORK]
    cmd += env_vars + [AGENT_BOT_DOCKER_IMAGE]

    try:
        subprocess.run(["docker", "rm", "-f", container_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        run_result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        rep.docker_container_name = container_name
        return True, (run_result.stdout.strip() or "کانتینر اجرا شد.")
    except Exception as e:
        return False, str(e)


def stop_representative_container(container_name: str) -> tuple[bool, str]:
    if not container_name:
        return False, "نام کانتینر ثبت نشده است."
    try:
        result = subprocess.run(["docker", "rm", "-f", container_name], capture_output=True, text=True, check=True)
        return True, (result.stdout.strip() or "کانتینر متوقف و حذف شد.")
    except Exception as e:
        return False, str(e)


def format_traffic(total_bytes: int) -> str:
    gb = (total_bytes or 0) / (1024 ** 3)
    return f"{gb:.2f} GB"


def calculate_org_user_financials(db, user_obj: User):
    active_configs = db.query(WireGuardConfig).filter(
        WireGuardConfig.user_telegram_id == user_obj.telegram_id,
        WireGuardConfig.status == "active"
    ).all()
    total_traffic_bytes = sum((cfg.cumulative_rx_bytes or 0) + (cfg.cumulative_tx_bytes or 0) for cfg in active_configs)
    total_traffic_gb = total_traffic_bytes / (1024 ** 3)
    price_per_gb = user_obj.org_price_per_gb or 0
    debt_amount = int(total_traffic_gb * price_per_gb)
    last_settlement = format_jalali_date(user_obj.org_last_settlement_at) if user_obj.org_last_settlement_at else "ثبت نشده"
    return {
        "active_configs": active_configs,
        "total_traffic_gb": total_traffic_gb,
        "price_per_gb": price_per_gb,
        "debt_amount": debt_amount,
        "last_settlement": last_settlement,
    }


def build_admin_user_info_message(db, user_obj: User) -> str:
    username = f"@{user_obj.username}" if user_obj.username else "ندارد"
    joined_date = format_jalali_date(user_obj.joined_at) if user_obj.joined_at else "نامشخص"
    all_configs_count = db.query(WireGuardConfig).filter(WireGuardConfig.user_telegram_id == user_obj.telegram_id).count()
    enterprise_status = "✅ مشتری سازمانی" if user_obj.is_organization_customer else "❌ مشتری عادی"
    blocked_status = "⛔ مسدود" if user_obj.is_blocked else "✅ فعال"
    msg = (
        f"👤 اطلاعات کاربر:\n\n"
        f"شناسه: {user_obj.telegram_id}\n"
        f"نام: {user_obj.first_name} {user_obj.last_name or ''}\n"
        f"نام کاربری: {username}\n"
        f"موجودی: {user_obj.wallet_balance:,} تومان\n"
        f"تاریخ عضویت: {joined_date}\n"
        f"وضعیت عضویت: {'✅ فعال' if user_obj.is_member else '❌ غیرفعال'}\n"
        f"ادمین: {'✅ بله' if user_obj.is_admin else '❌ خیر'}\n"
        f"وضعیت دسترسی: {blocked_status}\n"
        f"نوع مشتری: {enterprise_status}\n"
        f"تعداد لینک/کانفیگ‌ها: {all_configs_count}"
    )
    if user_obj.is_organization_customer:
        fz = calculate_org_user_financials(db, user_obj)
        msg += (
            f"\n\n🏢 اطلاعات مالی مشتری سازمانی:\n"
            f"• مجموع ترافیک لینک‌های فعال: {fz['total_traffic_gb']:.2f} GB\n"
            f"• هزینه هر گیگ: {fz['price_per_gb']:,} تومان\n"
            f"• مبلغ بدهکاری: {fz['debt_amount']:,} تومان\n"
            f"• زمان آخرین تسویه: {fz['last_settlement']}"
        )
    return msg


def get_admin_user_manage_view(db, user_obj: User, show_wallet_actions: bool = False, show_finance_panel: bool = False):
    username = f"@{user_obj.username}" if user_obj.username else "ندارد"
    joined_date = format_jalali_date(user_obj.joined_at) if user_obj.joined_at else "نامشخص"
    all_configs_count = db.query(WireGuardConfig).filter(WireGuardConfig.user_telegram_id == user_obj.telegram_id).count()
    financials = calculate_org_user_financials(db, user_obj) if user_obj.is_organization_customer else None

    return (
        "👤 مدیریت کاربر",
        get_admin_user_manage_keyboard(
            user_id=user_obj.id,
            telegram_id=user_obj.telegram_id,
            full_name=f"{user_obj.first_name or ''} {user_obj.last_name or ''}".strip() or "ندارد",
            username=username,
            wallet_balance=user_obj.wallet_balance or 0,
            joined_date=joined_date,
            is_member=bool(user_obj.is_member),
            is_admin=bool(user_obj.is_admin),
            config_count=all_configs_count,
            is_org=bool(user_obj.is_organization_customer),
            is_blocked=bool(user_obj.is_blocked),
            show_wallet_actions=show_wallet_actions,
            show_finance_panel=show_finance_panel,
            total_traffic_text=(f"{financials['total_traffic_gb']:.2f} GB" if financials else "-"),
            price_per_gb_text=(f"{financials['price_per_gb']:,} تومان" if financials else "-"),
            debt_text=(f"{financials['debt_amount']:,} تومان" if financials else "-"),
            last_settlement_text=(financials['last_settlement'] if financials else "-"),
        ),
    )


async def send_qr_code(sender, qr_base64: str, caption: str = None, chat_id: int = None):
    """
    Send QR code image from base64 string.
    Can use with message, callback.message, or bot.
    """
    import base64
    try:
        # Remove data:image/png;base64, prefix if present
        if ',' in qr_base64:
            qr_base64 = qr_base64.split(',')[1]
        
        # Decode base64
        image_data = base64.b64decode(qr_base64)
        
        # Create BufferedInputFile from bytes
        photo_file = BufferedInputFile(image_data, filename="qr_code.png")
        
        # Send photo
        if chat_id:
            # Using bot.send_photo
            await sender.send_photo(chat_id=chat_id, photo=photo_file, caption=caption)
        else:
            # Using message.answer_photo
            await sender.answer_photo(photo=photo_file, caption=caption)
                
    except Exception as e:
        print(f"Error sending QR code: {e}")


async def send_wireguard_config_file(sender, config_text: str, caption: str = None, chat_id: int = None):
    """Send wireguard config as .conf file."""
    import tempfile
    import os

    if not config_text:
        return

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False, encoding="utf-8") as tmp:
            tmp.write(config_text)
            tmp_path = tmp.name

        document = FSInputFile(tmp_path, filename="wireguard.conf")
        if chat_id:
            await sender.send_document(chat_id=chat_id, document=document, caption=caption or "📄 فایل کانفیگ WireGuard")
        else:
            await sender.answer_document(document=document, caption=caption or "📄 فایل کانفیگ WireGuard")
    except Exception as e:
        print(f"Error sending config file: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


def parse_ip_range(input_str: str) -> dict:
    """
    Parse IP range input in two formats:
    1. CIDR: x.y.z.0/24
    2. Range: x.y.z.10-x.y.z.220 or x.y.z.10-220
    
    Returns dict with keys: base_ip, start_ip, end_ip, cidr, is_range
    """
    input_str = input_str.strip()
    
    # Check if it's a range format (contains -)
    if '-' in input_str and '/' not in input_str:
        # Format: x.y.z.10-x.y.z.220 or x.y.z.10-220
        parts = input_str.split('-')
        if len(parts) == 2:
            start_ip = parts[0].strip()
            end_part = parts[1].strip()
            
            # Parse start IP
            start_parts = start_ip.split('.')
            if len(start_parts) == 4:
                base = '.'.join(start_parts[:3])
                start_last = int(start_parts[3])
                
                # Parse end IP - could be full IP or just last octet
                if '.' in end_part:
                    # Full IP like 192.168.30.220
                    end_parts = end_part.split('.')
                    end_last = int(end_parts[3])
                else:
                    # Just last octet like 220
                    end_last = int(end_part)
                
                return {
                    'base_ip': base,
                    'start_ip': start_ip,
                    'end_ip': f"{base}.{end_last}",
                    'cidr': None,
                    'is_range': True,
                    'start_last': start_last,
                    'end_last': end_last
                }
    
    # Check if it's CIDR format
    if '/' in input_str:
        # Format: x.y.z.0/24
        parts = input_str.split('/')
        if len(parts) == 2:
            ip = parts[0].strip()
            mask = int(parts[1].strip())
            
            # Calculate start and end IPs based on CIDR
            ip_parts = ip.split('.')
            if len(ip_parts) == 4 and 0 <= mask <= 32:
                ip_int = (int(ip_parts[0]) << 24) + (int(ip_parts[1]) << 16) + (int(ip_parts[2]) << 8) + int(ip_parts[3])
                mask_int = (0xFFFFFFFF << (32 - mask)) & 0xFFFFFFFF
                start_int = ip_int & mask_int
                end_int = start_int | (0xFFFFFFFF - mask_int)
                
                return {
                    'base_ip': ip,
                    'start_ip': f"{(start_int >> 24) & 0xFF}.{(start_int >> 16) & 0xFF}.{(start_int >> 8) & 0xFF}.{start_int & 0xFF}",
                    'end_ip': f"{(end_int >> 24) & 0xFF}.{(end_int >> 16) & 0xFF}.{(end_int >> 8) & 0xFF}.{end_int & 0xFF}",
                    'cidr': mask,
                    'is_range': False,
                    'start_last': start_int & 0xFF,
                    'end_last': end_int & 0xFF
                }
    
    # Default: treat as simple base (backward compatibility)
    parts = input_str.split('.')
    if len(parts) == 4:
        base = '.'.join(parts[:3])
        return {
            'base_ip': input_str,
            'start_ip': f"{base}.1",
            'end_ip': f"{base}.254",
            'cidr': 24,
            'is_range': False,
            'start_last': 1,
            'end_last': 254
        }
    
    return None


def get_server_field_prompt(field: str, step_num: int = None, total_steps: int = None) -> tuple:
    prompts = {
        "name": ("نام سرور را وارد کنید:", False),
        "host": ("IP/Host سرور را وارد کنید:", False),
        "api_port": ("پورت API (مثلاً 8728 یا 22):", False),
        "username": ("یوزرنیم API:", False),
        "password": ("پسورد API:", False),
        "wg_interface": ("نام اینترفیس وایرگارد:", False),
        "wg_server_public_key": ("Public Key سرور:", False),
        "wg_server_endpoint": ("Endpoint سرور:", False),
        "wg_server_port": ("پورت وایرگارد:", False),
        "wg_client_network_base": ("رنج IP را وارد کنید:\n• فرمت CIDR: 192.168.30.0/24\n• فرمت رنج: 192.168.30.10-192.168.30.220", False),
        "wg_client_dns": ("DNS (مثلاً 8.8.8.8,1.0.0.1):", False),
        "capacity": ("ظرفیت سرور (تعداد اکانت):", True)
    }
    msg, is_last = prompts.get(field, ("مقدار را وارد کنید:", False))
    return msg, is_last


def get_server_creation_steps():
    return ["name", "host", "api_port", "username", "password", "wg_interface", "wg_server_public_key", "wg_server_endpoint", "wg_server_port", "wg_client_network_base", "wg_client_dns", "capacity"]


def get_plan_creation_summary(data: dict) -> str:
    return (
        "➕ ایجاد پلن جدید\n\n"
        "اطلاعات وارد شده:\n"
        f"• نام: {data.get('name', '➖')}\n"
        f"• مدت: {data.get('days', '➖')} روز\n"
        f"• ترافیک: {data.get('traffic', '➖')} گیگ\n"
        f"• قیمت: {data.get('price', '➖')} تومان"
    )


def parse_positive_number(value: str, allow_float: bool = False):
    """Parse positive numeric input from Persian/Arabic/English digits."""
    normalized = normalize_numbers((value or "").strip()).replace("٫", ".").replace(",", ".")
    if allow_float:
        number = float(normalized)
    else:
        number = int(normalized)
    if number <= 0:
        raise ValueError
    return number


def format_gb_value(value) -> str:
    """Render traffic in GB without trailing .0 for integer values."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if numeric.is_integer():
        return str(int(numeric))
    return f"{numeric:g}"


def gregorian_to_jalali(g_date: datetime):
    gy = g_date.year - 1600
    gm = g_date.month - 1
    gd = g_date.day - 1

    g_day_no = 365 * gy + (gy + 3) // 4 - (gy + 99) // 100 + (gy + 399) // 400
    g_days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    for i in range(gm):
        g_day_no += g_days_in_month[i]
    if gm > 1 and ((gy + 1600) % 4 == 0 and ((gy + 1600) % 100 != 0 or (gy + 1600) % 400 == 0)):
        g_day_no += 1
    g_day_no += gd

    j_day_no = g_day_no - 79
    j_np = j_day_no // 12053
    j_day_no %= 12053

    jy = 979 + 33 * j_np + 4 * (j_day_no // 1461)
    j_day_no %= 1461

    if j_day_no >= 366:
        jy += (j_day_no - 1) // 365
        j_day_no = (j_day_no - 1) % 365

    if j_day_no < 186:
        jm = 1 + j_day_no // 31
        jd = 1 + j_day_no % 31
    else:
        jm = 7 + (j_day_no - 186) // 30
        jd = 1 + (j_day_no - 186) % 30

    return jy, jm, jd


def format_jalali_date(dt: datetime) -> str:
    if not dt:
        return "نامشخص"
    months = [
        "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
        "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
    ]
    jy, jm, jd = gregorian_to_jalali(dt)
    return f"{jd} {months[jm - 1]} {jy}"


def format_traffic_size(size_bytes: int) -> str:
    size_bytes = max(int(size_bytes or 0), 0)
    gib = 1024 ** 3
    mib = 1024 ** 2
    if size_bytes >= gib:
        return f"{size_bytes / gib:.2f} گیگابایت"
    return f"{size_bytes / mib:.2f} مگابایت"


def slugify_service_code(name: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_") or "service"


def get_plan_servers(db, plan_id: int):
    return db.query(Server).join(PlanServerMap, PlanServerMap.server_id == Server.id).filter(
        PlanServerMap.plan_id == plan_id,
        Server.is_active == True
    ).all()


def get_server_active_config_count(db, server_id: int) -> int:
    return db.query(WireGuardConfig).filter(WireGuardConfig.server_id == server_id, WireGuardConfig.status == "active").count()


def get_available_servers_for_plan(db, plan_id: int):
    servers = get_plan_servers(db, plan_id)
    available = []
    for srv in servers:
        used = get_server_active_config_count(db, srv.id)
        capacity = srv.capacity or 0
        if capacity <= 0 or used < capacity:
            available.append(srv)
    return available


def build_wg_kwargs(server: Server, user_id: str, plan, plan_name: str, duration_days: int):
    return dict(
        mikrotik_host=server.host,
        mikrotik_user=server.username or "",
        mikrotik_pass=server.password or "",
        mikrotik_port=server.api_port or 8728,
        wg_interface=server.wg_interface or WG_INTERFACE,
        wg_server_public_key=server.wg_server_public_key or WG_SERVER_PUBLIC_KEY,
        wg_server_endpoint=server.wg_server_endpoint or WG_SERVER_ENDPOINT,
        wg_server_port=server.wg_server_port or WG_SERVER_PORT,
        wg_client_network_base=server.wg_client_network_base or WG_CLIENT_NETWORK_BASE,
        wg_client_dns=server.wg_client_dns or WG_CLIENT_DNS,
        wg_ip_range_start=server.wg_ip_range_start if server.wg_is_ip_range else None,
        wg_ip_range_end=server.wg_ip_range_end if server.wg_is_ip_range else None,
        user_telegram_id=str(user_id),
        plan_id=plan.id if plan else None,
        plan_name=plan_name,
        duration_days=duration_days,
        server_id=server.id,
    )



# Messages
TEST_ACCOUNT_PLAN_NAME = "اکانت تست"

# Local messages that need dynamic values
MY_CONFIGS_MESSAGE = "🔗 کانفیگ های من\n\nشما هنوز کانفیگ فعالی ندارید.\n\nبرای خرید سرویس جدید، روی دکمه «🛒 خرید» کلیک کنید."
WALLET_MESSAGE = "💰 شارژ کیف پول\n\nموجودی فعلی شما: {balance} تومان\n\nبرای شارژ کیف پول، لطفاً با پشتیبانی تماس بگیرید."


# Message handlers
from aiogram import filters


@dp.message(filters.CommandStart())
async def start_handler(message: Message, bot):
    user = message.from_user
    user_id = user.id
    db = SessionLocal()
    try:
        is_member = await check_channel_member(bot, user_id, CHANNEL_ID)
        if is_member:
            db_user = get_or_create_user(db, str(user_id), user.username, user.first_name, user.last_name)
            if db_user.is_blocked:
                await message.answer("⛔ حساب شما توسط ادمین مسدود شده است.", parse_mode="HTML")
                return
            was_member = db_user.is_member
            db_user.is_member = True
            db.commit()
            await message.answer(WELCOME_MESSAGE, reply_markup=get_main_keyboard(db_user.is_admin), parse_mode="HTML")
            if not was_member:
                await message.answer("🎉 خوش آمدید! عضویت شما در کانال تایید شد.", parse_mode="HTML")
                for admin_id in ADMIN_IDS:
                    try:
                        username_text = f"@{db_user.username}" if db_user.username else "ندارد"
                        await bot.send_message(
                            chat_id=int(admin_id),
                            text=(
                                "👤 عضو جدید به ربات اضافه شد\n\n"
                                f"• آیدی: {db_user.telegram_id}\n"
                                f"• نام: {db_user.first_name or '-'} {db_user.last_name or ''}\n"
                                f"• نام کاربری: {username_text}"
                            ),
                            parse_mode="HTML"
                        )
                    except Exception:
                        pass
        else:
            db_user = get_user(db, str(user_id))
            if db_user:
                db_user.is_member = False
                db.commit()
            await message.answer(NOT_MEMBER_MESSAGE.format(channel_username=CHANNEL_USERNAME), parse_mode="HTML")
    except Exception as e:
        print(f"Error in start_handler: {e}")
        await message.answer("❌ خطایی رخ داد. لطفاً دوباره تلاش کنید.")
    finally:
        db.close()


@dp.message(filters.Command("register_panel"))
async def register_panel_handler(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ شما دسترسی ادمین ندارید.")
        return
    pending = load_pending_panel()
    if not pending:
        await message.answer("❌ درخواست پنل جدیدی وجود ندارد.\n\nابتدا agent را روی سرور اجرا کنید.")
        return
    msg = f"🔔 درخواست ثبت پنل جدید\n\n📍 اطلاعات پنل:\n• نام: {pending.get('name', 'Unknown')}\n• آی پی: {pending.get('ip', 'Unknown')}\n• لوکیشن: {pending.get('location', 'Unknown')}\n• پورت: {pending.get('port', 'Unknown')}\n• مسیر: {pending.get('path', '/')}\n\n📊 اطلاعات سیستم:\n• هاست نیم: {pending.get('system_info', {}).get('hostname', 'Unknown')}\n• سیستم عامل: {pending.get('system_info', {}).get('os', 'Unknown')}"
    await message.answer(msg, reply_markup=get_pending_panel_keyboard(), parse_mode="HTML")




@dp.message(lambda message: not is_admin(message.from_user.id) and (message.text or "").strip() in {
    "🛒 خرید جدید", "📱 نرم‌افزارها", "🔗 کانفیگ‌های من", "📖 آموزش اتصال", "📚 آموزش", "💰 کیف پول", "🧪 اکانت تست", "👤 حساب کاربری"
})
async def handle_user_menu_buttons(message: Message):
    text = (message.text or "").strip()
    user_id = message.from_user.id

    if text == "🛒 خرید جدید":
        db = SessionLocal()
        try:
            plans = db.query(Plan).filter(Plan.is_active == True).all()
            if plans:
                await message.answer("🛒 خرید سرویس وی پی ان\n\nیکی از پلن‌های زیر را انتخاب کنید:\n", reply_markup=get_buy_keyboard(plans), parse_mode="HTML")
            else:
                await message.answer("❌ در حال حاضر پلن فعالی برای خرید وجود ندارد.", parse_mode="HTML")
        finally:
            db.close()
        return

    if text == "📱 نرم‌افزارها":
        await message.answer(
            "📱 نرم‌افزارهای مورد نیاز\n\nبرای اتصال به وی‌پی‌ان از کانفیگ WireGuard استفاده کنید.\nنرم‌افزار مناسب سیستم‌عامل خود را دانلود کنید:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🍎 آیفون (iOS)", url="https://apps.apple.com/us/app/wireguard/id1441195209")],
                [InlineKeyboardButton(text="📱 اندروید", url="https://play.google.com/store/apps/details?id=com.wireguard.android&hl=en")],
                [InlineKeyboardButton(text="💻 ویندوز/مک/لینوکس", url="https://www.wireguard.com/install/")],
            ]),
            parse_mode="HTML"
        )
        return

    if text == "📖 آموزش اتصال":
        await message.answer(
            "📖 راهنمای اتصال به وی‌پی‌ان\n\nبرای اتصال به سرویس وی‌پی‌ان مراحل زیر را دنبال کنید:\n\n1️⃣ نرم‌افزار WireGuard را نصب کنید\n2️⃣ فایل کانفیگ را دریافت کنید\n3️⃣ فایل را در نرم‌افزار ایمپورت کنید\n4️⃣ به سرور متصل شوید\n\nبرای دریافت کانفیگ، به بخش «کانفیگ‌های من» مراجعه کنید.",
            parse_mode="HTML"
        )
        return

    if text == "🔗 کانفیگ‌های من":
        db = SessionLocal()
        try:
            configs = db.query(WireGuardConfig).filter(WireGuardConfig.user_telegram_id == str(user_id)).order_by(WireGuardConfig.created_at.desc()).all()
            if configs:
                await message.answer("🔗 کانفیگ های من\n\nبرای مشاهده جزئیات، کانفیگ موردنظر را انتخاب کنید:", reply_markup=get_configs_keyboard(configs), parse_mode="HTML")
            else:
                await message.answer(MY_CONFIGS_MESSAGE, parse_mode="HTML")
        finally:
            db.close()
        return

    if text == "💰 کیف پول":
        db = SessionLocal()
        try:
            user = get_user(db, str(user_id))
            await message.answer(WALLET_MESSAGE.format(balance=user.wallet_balance if user else 0), parse_mode="HTML")
        finally:
            db.close()
        return

    if text == "👤 حساب کاربری":
        await message.answer("برای مشاهده جزئیات حساب از دکمه‌های داخل صفحه استفاده کنید.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👤 نمایش حساب", callback_data="profile")]]), parse_mode="HTML")
        return

    if text == "🧪 اکانت تست":
        await message.answer("برای ایجاد اکانت تست روی دکمه زیر بزنید.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🧪 ایجاد اکانت تست", callback_data="test_account_create")]]), parse_mode="HTML")
        return

    if text == "📚 آموزش":
        await message.answer("📚 لیست آموزش‌ها:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📚 آموزش‌ها", callback_data="user_tutorials")]]), parse_mode="HTML")
        return

@dp.message(lambda message: is_admin(message.from_user.id))
async def handle_admin_input(message: Message):
    user_id = message.from_user.id
    text = message.text.strip()
    
    # Handle wallet adjust flow
    if user_id in admin_wallet_adjust_state:
        state = admin_wallet_adjust_state[user_id]
        amount = int(normalize_numbers(text)) if normalize_numbers(text).isdigit() else None
        if amount is None or amount < 0:
            await message.answer("❌ لطفاً عدد معتبر وارد کنید.", parse_mode="HTML")
            return
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == state["target_user_id"]).first()
            if not user:
                await message.answer("❌ کاربر یافت نشد.", parse_mode="HTML")
                return
            if state["op"] == "inc":
                user.wallet_balance += amount
            else:
                user.wallet_balance = max(0, user.wallet_balance - amount)
            db.commit()
            await message.answer(f"✅ موجودی جدید کاربر: {user.wallet_balance} تومان", parse_mode="HTML")
        finally:
            db.close()
            del admin_wallet_adjust_state[user_id]
        return

    # Handle discount create flow
    if user_id in admin_discount_state:
        state = admin_discount_state[user_id]
        step = state.get("step")
        if step == "code":
            state["code"] = text.strip().upper()
            state["step"] = "type"
            await message.answer("نوع تخفیف را وارد کنید: percent یا amount", parse_mode="HTML")
            return
        if step == "type":
            if text.lower() not in ["percent", "amount"]:
                await message.answer("❌ فقط percent یا amount", parse_mode="HTML")
                return
            state["type"] = text.lower()
            state["step"] = "value"
            await message.answer("مقدار تخفیف را وارد کنید.", parse_mode="HTML")
            return
        if step == "value":
            num = int(normalize_numbers(text)) if normalize_numbers(text).isdigit() else None
            if num is None or num <= 0:
                await message.answer("❌ مقدار نامعتبر", parse_mode="HTML")
                return
            state["value"] = num
            state["step"] = "max_uses"
            await message.answer("چند بار قابل استفاده باشد؟", parse_mode="HTML")
            return
        if step == "max_uses":
            num = int(normalize_numbers(text)) if normalize_numbers(text).isdigit() else None
            if num is None or num <= 0:
                await message.answer("❌ مقدار نامعتبر", parse_mode="HTML")
                return
            state["max_uses"] = num
            state["step"] = "valid_days"
            await message.answer("چند روز اعتبار داشته باشد؟", parse_mode="HTML")
            return
        if step == "valid_days":
            num = int(normalize_numbers(text)) if normalize_numbers(text).isdigit() else None
            if num is None or num <= 0:
                await message.answer("❌ مقدار نامعتبر", parse_mode="HTML")
                return
            db = SessionLocal()
            try:
                gift = GiftCode(
                    code=state["code"],
                    discount_percent=state["value"] if state["type"] == "percent" else None,
                    discount_amount=state["value"] if state["type"] == "amount" else None,
                    max_uses=state["max_uses"],
                    expires_at=datetime.utcnow() + timedelta(days=num),
                    is_active=True,
                )
                db.add(gift)
                db.commit()
                await message.answer("✅ کد تخفیف ساخته شد.", parse_mode="HTML")
            finally:
                db.close()
                del admin_discount_state[user_id]
            return

    # Handle receipt reject flow
    if user_id in admin_receipt_reject_state:
        state = admin_receipt_reject_state[user_id]
        receipt_id = state.get("receipt_id")
        reject_reason = text.strip()
        
        db = SessionLocal()
        try:
            receipt = db.query(PaymentReceipt).filter(PaymentReceipt.id == receipt_id).first()
            if receipt:
                receipt.status = "rejected"
                db.commit()
                
                # Notify user about rejection
                try:
                    user_tg_id = int(receipt.user_telegram_id)
                    await message.bot.send_message(
                        chat_id=user_tg_id,
                        text=f"❌ پرداخت شما رد شد.\n\n📋 دلیل: {reject_reason}\n\nبرای اطلاعات بیشتر با پشتیبانی تماس بگیرید.",
                        parse_mode="HTML"
                    )
                except Exception as e:
                    print(f"Error notifying user about rejection: {e}")
                
                await message.answer(f"✅ فیش رد شد و کاربر اطلاع داده شد.\n📋 دلیل: {reject_reason}", reply_markup=get_receipt_done_keyboard(), parse_mode="HTML")
            else:
                await message.answer("❌ فیش پرداخت یافت نشد.", parse_mode="HTML")
        except Exception as e:
            await message.answer(f"❌ خطا: {str(e)}", parse_mode="HTML")
        finally:
            db.close()
            del admin_receipt_reject_state[user_id]
        return
    
    # Handle service type create flow
    if user_id in admin_service_type_state:
        state = admin_service_type_state[user_id]
        if state.get("step") == "name":
            name = text.strip()
            if not name:
                await message.answer("❌ نام نوع سرویس نامعتبر است.", parse_mode="HTML")
                return
            code = slugify_service_code(name)
            db = SessionLocal()
            try:
                exists = db.query(ServiceType).filter(ServiceType.code == code).first()
                if exists:
                    await message.answer("❌ این نوع سرویس قبلاً ثبت شده است.", parse_mode="HTML")
                    return
                row = ServiceType(name=name, code=code, is_active=True)
                db.add(row)
                db.commit()
                await message.answer(f"✅ نوع سرویس {name} اضافه شد.", parse_mode="HTML")
            finally:
                db.close()
                admin_service_type_state.pop(user_id, None)
            return

    # Handle tutorial create flow
    if user_id in admin_tutorial_state:
        state = admin_tutorial_state[user_id]
        step = state.get("step")
        
        # Check for cancel
        if text.strip() == "انصراف" or text.strip() == "cancel":
            del admin_tutorial_state[user_id]
            await message.answer("❌ عملیات لغو شد.", parse_mode="HTML")
            return
        
        if step == "title":
            state["title"] = text.strip()
            state["step"] = "description"
            await message.answer(
                "✅ عنوان ثبت شد.\n\n"
                "حالا لطفاً متن آموزش را وارد کنید:\n"
                "(می‌تواند خالی باشد)",
                parse_mode="HTML"
            )
            return
        
        if step == "description":
            state["description"] = text.strip()
            state["step"] = "media"
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            await message.answer(
                "✅ متن ثبت شد.\n\n"
                "حالا عکس یا ویدیوی آموزش را آپلود کنید:\n"
                "(اگر نمی‌خواهید رسانه‌ای اضافه کنید، دکمه زیر را بزنید)",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⏭️ بدون رسانه", callback_data=f"admin_tutorial_skip_media_{state.get('service_type_id')}")]
                ]),
                parse_mode="HTML"
            )
            return

    # Handle representative create flow
    if user_id in admin_representative_state:
        state = admin_representative_state[user_id]
        step = state.get("step")

        if step == "name":
            state["name"] = text.strip()
            state["step"] = "bot_token"
            await message.answer("توکن ربات نمایندگی را وارد کنید:", parse_mode="HTML")
            return

        if step == "bot_token":
            if ":" not in text.strip():
                await message.answer("❌ توکن ربات معتبر نیست.", parse_mode="HTML")
                return
            state["bot_token"] = text.strip()
            state["step"] = "admin_id"
            await message.answer("آیدی تلگرام ادمین نمایندگی را وارد کنید:", parse_mode="HTML")
            return

        if step == "admin_id":
            normalized = normalize_numbers(text.strip())
            if not normalized.isdigit():
                await message.answer("❌ آیدی ادمین باید عددی باشد.", parse_mode="HTML")
                return
            state["admin_telegram_id"] = normalized
            state["step"] = "channel_id"
            await message.answer("آیدی یا یوزرنیم کانال نمایندگی را وارد کنید (مثل @mychannel یا -100...):", parse_mode="HTML")
            return

        if step == "channel_id":
            channel_id = text.strip().replace(" ", "")
            if not channel_id:
                await message.answer("❌ آیدی کانال نامعتبر است.", parse_mode="HTML")
                return

            db = SessionLocal()
            try:
                rep = Representative(
                    name=state.get("name") or "نمایندگی",
                    bot_token=state.get("bot_token"),
                    admin_telegram_id=state.get("admin_telegram_id"),
                    channel_id=channel_id,
                    is_active=True,
                )
                db.add(rep)
                db.commit()
                db.refresh(rep)

                ok, output = start_representative_container(rep)
                rep.is_active = ok
                db.commit()

                status = "✅ نمایندگی ساخته شد و کانتینر اجرا شد." if ok else "⚠️ نمایندگی ثبت شد اما اجرای کانتینر ناموفق بود."
                await message.answer(
                    f"{status}\n\n"
                    f"• نام: {rep.name}\n"
                    f"• کانال: {rep.channel_id}\n"
                    f"• کانتینر: {rep.docker_container_name or '-'}\n"
                    f"• نتیجه: {output[:500]}",
                    parse_mode="HTML"
                )
            finally:
                db.close()
                admin_representative_state.pop(user_id, None)
            return

    # Handle server create/edit flow
    if user_id in admin_server_state:
        state = admin_server_state[user_id]
        
        # Check for cancel
        if text.strip() == "انصراف" or text.strip() == "cancel":
            del admin_server_state[user_id]
            await message.answer("❌ عملیات لغو شد.", parse_mode="HTML")
            return
        
        if state.get("step") == "edit_capacity":
            db = SessionLocal()
            try:
                srv = db.query(Server).filter(Server.id == state.get("server_id")).first()
                if not srv:
                    await message.answer("❌ سرور یافت نشد.", parse_mode="HTML")
                    return
                srv.capacity = int(normalize_numbers(text) or 0)
                db.commit()
                await message.answer("✅ ظرفیت سرور ویرایش شد.", parse_mode="HTML")
            finally:
                db.close()
                admin_server_state.pop(user_id, None)
            return

        steps = get_server_creation_steps()
        current = state.get("step")
        if current in steps:
            # Validate IP range input
            if current == "wg_client_network_base":
                parsed = parse_ip_range(text.strip())
                if not parsed:
                    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                    await message.answer(
                        "❌ فرمت رنج IP نامعتبر است.\n• CIDR: 192.168.30.0/24\n• رنج: 192.168.30.10-192.168.30.220",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="❌ انصراف", callback_data="server_add_cancel")]
                        ]),
                        parse_mode="HTML"
                    )
                    return
                # Store the parsed info
                state["wg_client_network_base"] = parsed["base_ip"]
                state["wg_ip_range_start"] = parsed.get("start_last", 1)
                state["wg_ip_range_end"] = parsed.get("end_last", 254)
                state["wg_is_ip_range"] = parsed.get("is_range", False)
            else:
                state[current] = text.strip()
            idx = steps.index(current)
            if idx < len(steps) - 1:
                state["step"] = steps[idx + 1]
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                msg, _ = get_server_field_prompt(steps[idx + 1])
                await message.answer(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="❌ انصراف", callback_data="server_add_cancel")]
                ]), parse_mode="HTML")
                return

            db = SessionLocal()
            try:
                srv = Server(
                    name=state.get("name"),
                    service_type_id=state.get("service_type_id"),
                    host=state.get("host"),
                    api_port=int(normalize_numbers(state.get("api_port", "8728")) or 8728),
                    username=state.get("username"),
                    password=state.get("password"),
                    wg_interface=state.get("wg_interface"),
                    wg_server_public_key=state.get("wg_server_public_key"),
                    wg_server_endpoint=state.get("wg_server_endpoint"),
                    wg_server_port=int(normalize_numbers(state.get("wg_server_port", "51820")) or 51820),
                    wg_client_network_base=state.get("wg_client_network_base"),
                    wg_ip_range_start=state.get("wg_ip_range_start"),
                    wg_ip_range_end=state.get("wg_ip_range_end"),
                    wg_is_ip_range=state.get("wg_is_ip_range", False),
                    wg_client_dns=state.get("wg_client_dns"),
                    capacity=int(normalize_numbers(state.get("capacity", "100")) or 100),
                    is_active=True,
                )
                db.add(srv)
                db.commit()
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                await message.answer(
                    f"✅ سرور {srv.name} ثبت شد.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_servers")],
                        [InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="back_to_main")]
                    ]),
                    parse_mode="HTML"
                )
            except Exception as e:
                await message.answer(f"❌ خطا در ثبت سرور: {e}", parse_mode="HTML")
            finally:
                db.close()
                admin_server_state.pop(user_id, None)
            return

    # Handle custom account creation flow
    if user_id in admin_create_account_state:
        state = admin_create_account_state[user_id]
        step = state.get("step")
        
        if step == "name":
            # Validate name input
            account_name = text.strip()
            if not account_name:
                await message.answer("❌ لطفاً نام معتبر وارد کنید.", parse_mode="HTML")
                return
            state["name"] = account_name
            state["step"] = "days"
            await message.answer(f"✅ نام اکانت: {account_name}\n\nحالا لطفاً تعداد روز را وارد کنید:\n(عدد صحیح)", parse_mode="HTML")
            return
        
        if step == "days":
            # Validate days input
            text_normalized = normalize_numbers(text)
            try:
                days = int(text_normalized)
                if days <= 0:
                    await message.answer("❌ لطفاً یک عدد مثبت وارد کنید.", parse_mode="HTML")
                    return
                state["days"] = days
                state["step"] = "traffic"
                await message.answer(f"✅ تعداد روز: {days} روز\n\nحالا لطفاً میزان حجم را به گیگابایت وارد کنید:", parse_mode="HTML")
            except ValueError:
                await message.answer("❌ لطفاً یک عدد صحیح وارد کنید.", parse_mode="HTML")
                return
        
        elif step == "traffic":
            # Validate traffic input
            text_normalized = normalize_numbers(text)
            try:
                traffic = int(text_normalized)
                if traffic <= 0:
                    await message.answer("❌ لطفاً یک عدد مثبت وارد کنید.", parse_mode="HTML")
                    return
                state["traffic"] = traffic
                days = state.get("days", 0)
                account_name = state.get("name", "")
                
                # Create WireGuard account with custom plan
                try:
                    import wireguard
                    wg_result = wireguard.create_wireguard_account(
                        mikrotik_host=MIKROTIK_HOST,
                        mikrotik_user=MIKROTIK_USER,
                        mikrotik_pass=MIKROTIK_PASS,
                        mikrotik_port=MIKROTIK_PORT,
                        wg_interface=WG_INTERFACE,
                        wg_server_public_key=WG_SERVER_PUBLIC_KEY,
                        wg_server_endpoint=WG_SERVER_ENDPOINT,
                        wg_server_port=WG_SERVER_PORT,
                        wg_client_network_base=WG_CLIENT_NETWORK_BASE,
                        wg_client_dns=WG_CLIENT_DNS,
                        user_telegram_id=str(user_id),
                        plan_id=None,
                        plan_name=account_name,
                        duration_days=days
                    )
                    
                    if wg_result.get("success"):
                        client_ip = wg_result.get("client_ip", "N/A")
                        config = wg_result.get("config", "")
                        
                        # Send summary + config file + QR to admin
                        await message.answer(
                            f"✅ اکانت وایرگارد دلخواه ایجاد شد!\n\n📋 اطلاعات اکانت:\n• مدت: {days} روز\n• حجم: {traffic} گیگ\n• آی پی: {client_ip}",
                            parse_mode="HTML"
                        )
                        
                        # Send config file
                        if config:
                            await send_wireguard_config_file(
                                message,
                                config,
                                caption="📄 فایل کانفیگ WireGuard"
                            )
                        
                        # Send QR if available
                        if wg_result.get("qr_code"):
                            await send_qr_code(
                                message,
                                wg_result.get("qr_code"),
                                f"QR Code - {days}روز / {traffic}گیگ"
                            )
                            await message.answer(
                                f"🏷 نام کانفیگ: <code>{wg_result.get('peer_comment', 'نامشخص')}</code>\n"
                                f"📦 پلن انتخابی: {account_name}",
                                parse_mode="HTML"
                            )
                    else:
                        await message.answer(
                            f"❌ خطا در ایجاد اکانت: {wg_result.get('error', 'خطای نامشخص')}",
                            parse_mode="HTML"
                        )
                except Exception as e:
                    await message.answer(f"❌ خطا در ایجاد اکانت: {str(e)}", parse_mode="HTML")
                finally:
                    # Clear state
                    if user_id in admin_create_account_state:
                        del admin_create_account_state[user_id]
            except ValueError:
                await message.answer("❌ لطفاً یک عدد صحیح وارد کنید.", parse_mode="HTML")
                return
        
        return
    
    if user_id in admin_plan_state:
        state = admin_plan_state[user_id]

        if state.get("action") == "test_account_setup":
            step = state.get("step")
            try:
                value = parse_positive_number(text, allow_float=(step == "traffic"))
            except ValueError:
                if step == "traffic":
                    await message.answer(
                        "❌ لطفاً حجم را به‌صورت عدد بزرگ‌تر از صفر وارد کنید (مثلاً <code>1</code> یا <code>0.5</code>).",
                        parse_mode="HTML"
                    )
                else:
                    await message.answer("❌ لطفاً یک عدد صحیح بزرگ‌تر از صفر وارد کنید.", parse_mode="HTML")
                return

            if step == "days":
                state["days"] = int(value)
                state["step"] = "traffic"
                await message.answer(
                    "🌐 لطفاً حجم اکانت تست را به گیگ وارد کنید (مثلاً <code>1</code> یا <code>0.5</code>):",
                    parse_mode="HTML"
                )
                return

            if step == "traffic":
                days = state.get("days")
                traffic = float(value)
                db = SessionLocal()
                try:
                    test_plan = db.query(Plan).filter(Plan.name == TEST_ACCOUNT_PLAN_NAME).first()
                    if test_plan:
                        test_plan.duration_days = days
                        test_plan.traffic_gb = traffic
                        test_plan.price = 0
                        test_plan.is_active = True
                        test_plan.description = "پلن تست یک‌بار مصرف"
                        action_text = "به‌روزرسانی شد"
                    else:
                        test_plan = Plan(
                            name=TEST_ACCOUNT_PLAN_NAME,
                            duration_days=days,
                            traffic_gb=traffic,
                            price=0,
                            is_active=True,
                            description="پلن تست یک‌بار مصرف",
                        )
                        db.add(test_plan)
                        action_text = "ایجاد شد"

                    db.commit()
                    await message.answer(
                        f"✅ اکانت تست با موفقیت {action_text}.\n\n• مدت: {days} روز\n• حجم: {format_gb_value(traffic)} گیگ",
                        parse_mode="HTML"
                    )
                    all_plans = db.query(Plan).all()
                    await message.answer(PLANS_MESSAGE, reply_markup=get_plans_keyboard(all_plans), parse_mode="HTML")
                finally:
                    db.close()
                    admin_plan_state.pop(user_id, None)
                return

        step = state.get("step")
        field = state.get("field")

        if step:
            if step in ["days", "traffic", "price"]:
                text = normalize_numbers(text)
                try:
                    int(text)
                except ValueError:
                    await message.answer("❌ لطفاً یک عدد صحیح وارد کنید.", parse_mode="HTML")
                    return

            state.setdefault("data", {})[step] = text

            next_steps = {
                "name": "days",
                "days": "traffic",
                "traffic": "price",
            }

            next_step = next_steps.get(step)
            if next_step:
                state["step"] = next_step
                await message.answer(get_plan_field_prompt(next_step), parse_mode="HTML")
            else:
                state.pop("step", None)
                if state.get("action") == "create" and state.get("plan_id") == "new":
                    db = SessionLocal()
                    try:
                        plan_data = state.get("data", {})
                        plan = Plan(
                            name=plan_data["name"],
                            duration_days=int(plan_data["days"]),
                            traffic_gb=int(plan_data["traffic"]),
                            price=int(plan_data["price"]),
                            description=plan_data.get("description", "")
                        )
                        db.add(plan)
                        db.commit()

                        await message.answer(
                            f"✅ پلن «{plan.name}» با موفقیت ایجاد شد.\n\n" + get_plan_creation_summary(state["data"]),
                            parse_mode="HTML"
                        )
                        all_plans = db.query(Plan).all()
                        await message.answer(PLANS_MESSAGE, reply_markup=get_plans_keyboard(all_plans), parse_mode="HTML")
                    finally:
                        db.close()
                        admin_plan_state.pop(user_id, None)
                else:
                    await message.answer(
                        get_plan_creation_summary(state["data"]),
                        reply_markup=get_plan_edit_keyboard(plan_id=None),
                        parse_mode="HTML"
                    )
            return
        
        if field:
            if field in ["days", "traffic", "price"]:
                text = normalize_numbers(text)
                try:
                    int(text)
                except ValueError:
                    await message.answer("❌ لطفاً یک عدد صحیح وارد کنید.", parse_mode="HTML")
                    return
            state.setdefault("data", {})[field] = text
            plan_id = state.get("plan_id", "new")
            action = "ویرایش" if state.get("action") == "edit" else "ایجاد"
            if plan_id == "new":
                await message.answer(f"➕ {action} پلن جدید\n\nاطلاعات وارد شده:\n• نام: {state['data'].get('name', '➖')}\n• مدت: {state['data'].get('days', '➖')} روز\n• ترافیک: {state['data'].get('traffic', '➖')} گیگ\n• قیمت: {state['data'].get('price', '➖')} تومان\n• توضیحات: {state['data'].get('description', '➖')}", reply_markup=get_plan_edit_keyboard(plan_id=None), parse_mode="HTML")
            else:
                await message.answer(f"✏️ {action} پلن\n\nاطلاعات وارد شده:\n• نام: {state['data'].get('name', '➖')}\n• مدت: {state['data'].get('days', '➖')} روز\n• ترافیک: {state['data'].get('traffic', '➖')} گیگ\n• قیمت: {state['data'].get('price', '➖')} تومان\n• توضیحات: {state['data'].get('description', '➖')}", reply_markup=get_plan_edit_keyboard(plan_id=int(plan_id)), parse_mode="HTML")
            return

        await message.answer("❌ لطفاً از دکمه‌های مدیریت پلن استفاده کنید.", parse_mode="HTML")
        return
    
    admin_menu_map = {
        "⚙️ مدیریت": "main_admin",
        "🖥️ پنل‌ها": "admin_panels",
        "🔍 جستجو": "admin_search_user",
        "📦 پلن ها": "admin_plans",
        "💳 فیش‌های پرداخت": "admin_receipts",
        "🎁 کد تخفیف": "admin_discount_create",
        "🧩 انواع سرویس": "admin_service_types",
        "🖧 مدیریت سرورها": "admin_servers",
        "🔗 ساخت اکانت": "admin_create_account",
        "🤝 نمایندگی‌ها": "admin_representatives",
        "📚 آموزش ادمین": "admin_tutorials",
        "🔔 درخواست پنل جدید": "admin_pending_panel",
        "🔙 بازگشت": "back_to_main",
    }
    if text in admin_menu_map:
        action = admin_menu_map[text]
        if action == "main_admin":
            pending_panel = load_pending_panel()
            await message.answer(ADMIN_MESSAGE, reply_markup=get_admin_keyboard(pending_panel), parse_mode="HTML")
            return
        if action == "admin_search_user":
            admin_user_search_state[user_id] = {"active": True}
            await message.answer(SEARCH_USER_MESSAGE, parse_mode="HTML")
            return
        await message.answer("از دکمه‌های داخل صفحه استفاده کنید:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="▶️ باز کردن بخش", callback_data=action)]]), parse_mode="HTML")
        return

    if user_id in admin_user_search_state:
        query = text.strip().lower()
        db = SessionLocal()
        try:
            # Use case-insensitive partial matching with like
            from sqlalchemy import or_
            search_pattern = f"%{query}%"
            users = db.query(User).filter(
                or_(
                    User.telegram_id.ilike(search_pattern),
                    User.username.ilike(search_pattern),
                    User.first_name.ilike(search_pattern),
                    User.last_name.ilike(search_pattern)
                )
            ).all()
            
            # Also check full name combination
            if not users:
                all_users = db.query(User).all()
                found = []
                for u in all_users:
                    full_name = f"{u.first_name or ''} {u.last_name or ''}".strip().lower()
                    if query in full_name:
                        found.append(u)
                users = found
            
            if users:
                await message.answer("نتایج جستجو:", reply_markup=get_found_users_keyboard(users), parse_mode="HTML")
            else:
                await message.answer("❌ کاربری یافت نشد.", parse_mode="HTML")
        finally:
            db.close()
            del admin_user_search_state[user_id]
        return

    db = SessionLocal()
    try:
        user = get_user(db, text) or db.query(User).filter(User.username == text).first()
        if user:
            joined_date = format_jalali_date(user.joined_at) if user.joined_at else "نامشخص"
            msg = f"👤 اطلاعات کاربر:\n\nشناسه: {user.telegram_id}\nنام: {user.first_name}\nنام کاربری: @{user.username}\nموجودی: {user.wallet_balance} تومان\nتاریخ عضویت: {joined_date}\nوضعیت: {'✅ فعال' if user.is_member else '❌ غیرفعال'}\nادمین: {'✅ بله' if user.is_admin else '❌ خیر'}"
            await message.answer(msg, parse_mode="HTML")
        else:
            await message.answer("❌ کاربر یافت نشد.", parse_mode="HTML")
    finally:
        db.close()


@dp.callback_query()
async def callback_handler(callback: CallbackQuery, bot):
    data = callback.data
    user_id = callback.from_user.id
    
    if data.startswith(("admin_", "panel_", "plan_", "rep_")) or data == "admin":
        if not is_admin(user_id):
            await callback.answer("❌ شما دسترسی مدیریت ندارید.", show_alert=True)
            return

    if not is_admin(user_id):
        db_guard = SessionLocal()
        try:
            current_user = get_user(db_guard, str(user_id))
            if current_user and current_user.is_blocked:
                await callback.answer("⛔ حساب شما مسدود است.", show_alert=True)
                return
        finally:
            db_guard.close()
    
    # === USER CALLBACKS ===
    if data == "buy":
        db = SessionLocal()
        try:
            plans = db.query(Plan).filter(Plan.is_active == True).all()
            if plans:
                await callback.message.answer("🛒 خرید سرویس وی پی ان\n\nیکی از پلن‌های زیر را انتخاب کنید:\n", reply_markup=get_buy_keyboard(plans), parse_mode="HTML")
            else:
                await callback.message.answer("❌ در حال حاضر پلن فعالی برای خرید وجود ندارد.", parse_mode="HTML")
        finally:
            db.close()
    
    elif data == "test_account_create":
        db = SessionLocal()
        try:
            user = get_or_create_user(
                db,
                str(user_id),
                callback.from_user.username,
                callback.from_user.first_name,
                callback.from_user.last_name,
            )
            if user.has_used_test_account:
                await callback.message.answer("❌ شما قبلاً از اکانت تست استفاده کرده‌اید و فقط یک‌بار مجاز هستید.", parse_mode="HTML")
                return

            plan = db.query(Plan).filter(Plan.name == TEST_ACCOUNT_PLAN_NAME, Plan.is_active == True).first()
            if not plan:
                await callback.message.answer("❌ پلن «اکانت تست» یافت نشد یا غیرفعال است.", parse_mode="HTML")
                return

            try:
                import wireguard
                available_servers = get_available_servers_for_plan(db, plan.id)
                server = available_servers[0] if available_servers else None
                if server:
                    wg_result = wireguard.create_wireguard_account(**build_wg_kwargs(server, str(user_id), plan, plan.name, plan.duration_days))
                else:
                    wg_result = wireguard.create_wireguard_account(
                        mikrotik_host=MIKROTIK_HOST,
                        mikrotik_user=MIKROTIK_USER,
                        mikrotik_pass=MIKROTIK_PASS,
                        mikrotik_port=MIKROTIK_PORT,
                        wg_interface=WG_INTERFACE,
                        wg_server_public_key=WG_SERVER_PUBLIC_KEY,
                        wg_server_endpoint=WG_SERVER_ENDPOINT,
                        wg_server_port=WG_SERVER_PORT,
                        wg_client_network_base=WG_CLIENT_NETWORK_BASE,
                        wg_client_dns=WG_CLIENT_DNS,
                        user_telegram_id=str(user_id),
                        plan_id=plan.id,
                        plan_name=plan.name,
                        duration_days=plan.duration_days,
                    )
            except Exception as e:
                await callback.message.answer(f"❌ خطا در ایجاد اکانت تست: {str(e)}", parse_mode="HTML")
                return

            if not wg_result.get("success"):
                await callback.message.answer(
                    f"❌ خطا در ایجاد اکانت تست: {wg_result.get('error', 'خطای نامشخص')}",
                    parse_mode="HTML"
                )
                return

            user.has_used_test_account = True
            db.commit()

            client_ip = wg_result.get("client_ip", "N/A")
            config_text = wg_result.get("config", "")
            await callback.message.answer(
                (
                    f"✅ اکانت تست شما ساخته شد.\n\n"
                    f"• پلن: {plan.name}\n"
                    f"• مدت: {plan.duration_days} روز\n"
                    f"• حجم: {plan.traffic_gb} گیگ\n"
                    f"• قیمت: {plan.price:,} تومان\n"
                    f"• آی‌پی: {client_ip}\n\n"
                    "📥 فایل کانفیگ و QR Code ارسال شد."
                ),
                parse_mode="HTML"
            )

            if config_text:
                await send_wireguard_config_file(
                    callback.message,
                    config_text,
                    caption="📄 فایل کانفیگ WireGuard (اکانت تست)",
                )

            if wg_result.get("qr_code"):
                await send_qr_code(
                    callback.message,
                    wg_result.get("qr_code"),
                    caption=(
                        "📷 QR Code اکانت تست\n\n"
                        f"🏷 نام کانفیگ: <code>{wg_result.get('peer_comment', 'نامشخص')}</code>\n"
                        f"📦 پلن انتخابی: {plan.name}"
                    ),
                )
        finally:
            db.close()

    elif data == "software":
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        await callback.message.answer(
            "📱 نرم‌افزارهای مورد نیاز\n\n"
            "برای اتصال به وی‌پی‌ان از کانفیگ WireGuard استفاده کنید.\n"
            "نرم‌افزار مناسب سیستم‌عامل خود را دانلود کنید:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🍎 آیفون (iOS)", url="https://apps.apple.com/us/app/wireguard/id1441195209")],
                [InlineKeyboardButton(text="📱 اندروید", url="https://play.google.com/store/apps/details?id=com.wireguard.android&hl=en")],
                [InlineKeyboardButton(text="💻 ویندوز/مک/لینوکس", url="https://www.wireguard.com/install/")],
                [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]
            ]),
            parse_mode="HTML"
        )
    
    elif data == "howto":
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        await callback.message.answer(
            "📖 راهنمای اتصال به وی‌پی‌ان\n\n"
            "برای اتصال به سرویس وی‌پی‌ان مراحل زیر را دنبال کنید:\n\n"
            "1️⃣ نرم‌افزار WireGuard را نصب کنید\n"
            "2️⃣ فایل کانفیگ را دریافت کنید\n"
            "3️⃣ فایل را در نرم‌افزار ایمپورت کنید\n"
            "4️⃣ به سرور متصل شوید\n\n"
            "برای دریافت کانفیگ، به بخش «کانفیگ‌های من» مراجعه کنید.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔗 دریافت کانفیگ", callback_data="configs")],
                [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]
            ]),
            parse_mode="HTML"
        )
    
    elif data == "configs":
        db = SessionLocal()
        try:
            configs = db.query(WireGuardConfig).filter(
                WireGuardConfig.user_telegram_id == str(user_id)
            ).order_by(WireGuardConfig.created_at.desc()).all()
            if configs:
                await callback.message.answer(
                    "🔗 کانفیگ های من\n\nبرای مشاهده جزئیات، کانفیگ موردنظر را انتخاب کنید:",
                    reply_markup=get_configs_keyboard(configs),
                    parse_mode="HTML"
                )
            else:
                await callback.message.answer(MY_CONFIGS_MESSAGE, parse_mode="HTML")
        finally:
            db.close()

    elif data.startswith("cfg_view_"):
        config_id = data.replace("cfg_view_", "")
        db = SessionLocal()
        try:
            config = db.query(WireGuardConfig).filter(
                WireGuardConfig.id == int(config_id)
            ).first()
            if not config:
                await callback.message.answer("❌ کانفیگ یافت نشد.", parse_mode="HTML")
                return

            # Check if user is the owner or admin
            is_owner = str(user_id) == config.user_telegram_id
            is_admin_user = is_admin(user_id)
            
            if not is_owner and not is_admin_user:
                await callback.message.answer("❌ شما دسترسی ندارید.", parse_mode="HTML")
                return

            plan = None
            plan_traffic_bytes = 0
            if config.plan_id:
                plan = db.query(Plan).filter(Plan.id == config.plan_id).first()
                if plan:
                    plan_traffic_bytes = (plan.traffic_gb or 0) * (1024 ** 3)

            consumed_bytes = config.cumulative_rx_bytes or 0
            remaining_bytes = max(plan_traffic_bytes - consumed_bytes, 0) if plan_traffic_bytes else 0
            expires_at = config.expires_at
            if not expires_at and plan and plan.duration_days:
                expires_at = config.created_at + timedelta(days=plan.duration_days)

            now = datetime.utcnow()
            is_expired_by_date = bool(expires_at and expires_at <= now)
            is_expired_by_traffic = bool(plan_traffic_bytes and remaining_bytes <= 0)
            is_disabled = config.status in ["expired", "revoked", "disabled"]
            can_renew = bool(config.plan_id and (is_expired_by_date or is_expired_by_traffic or is_disabled))

            msg = (
                "📋 جزئیات کانفیگ\n\n"
                f"• پلن: {config.plan_name or 'نامشخص'}\n"
                f"• آی پی: {config.client_ip}\n"
                f"• تاریخ خرید: {format_jalali_date(config.created_at)}\n"
                f"• تاریخ انقضا: {format_jalali_date(expires_at)}\n"
                f"• وضعیت: {'🔴 غیرفعال' if can_renew else '🟢 فعال'}\n"
                f"• حجم مصرفی: {format_traffic_size(consumed_bytes)}\n"
                f"• حجم دریافتی (RX): {format_traffic_size(config.cumulative_rx_bytes or 0)}\n"
                f"• حجم ارسالی (TX): {format_traffic_size(config.cumulative_tx_bytes or 0)}\n"
                f"• حجم باقی‌مانده: {format_traffic_size(remaining_bytes) if plan_traffic_bytes else 'نامحدود/نامشخص'}"
            )
            owner_user = db.query(User).filter(User.telegram_id == config.user_telegram_id).first()
            is_org_customer = bool(owner_user and owner_user.is_organization_customer)
            financials = calculate_org_user_financials(db, owner_user) if owner_user and is_org_customer else None
            await callback.message.answer(
                msg,
                reply_markup=get_config_detail_keyboard(
                    config.id,
                    can_renew=can_renew,
                    is_org_customer=is_org_customer,
                    total_traffic_text=(f"{financials['total_traffic_gb']:.2f} GB" if financials else "-"),
                    price_per_gb_text=(f"{financials['price_per_gb']:,} تومان" if financials else "-"),
                    debt_text=(f"{financials['debt_amount']:,} تومان" if financials else "-"),
                    last_settlement_text=(financials['last_settlement'] if financials else "-"),
                ),
                parse_mode="HTML"
            )
        finally:
            db.close()

    elif data == "admin_user_info_ro":
        await callback.answer("این بخش فقط جهت نمایش است.", show_alert=False)

    elif data.startswith("cfg_enterprise_ro_"):
        await callback.answer("این بخش فقط جهت نمایش است و توسط ادمین مدیریت می‌شود.", show_alert=True)

    elif data.startswith("cfg_renew_unavailable_"):
        await callback.message.answer("ℹ️ گزینه تمدید زمانی فعال می‌شود که سرویس غیرفعال یا منقضی شده باشد.", parse_mode="HTML")

    elif data.startswith("cfg_renew_"):
        config_id = int(data.replace("cfg_renew_", ""))
        db = SessionLocal()
        try:
            config = db.query(WireGuardConfig).filter(
                WireGuardConfig.id == config_id
            ).first()
            if not config or not config.plan_id:
                await callback.message.answer("❌ امکان تمدید برای این کانفیگ وجود ندارد.", parse_mode="HTML")
                return

            # Check if user is the owner or admin
            is_owner = str(user_id) == config.user_telegram_id
            is_admin_user = is_admin(user_id)
            
            if not is_owner and not is_admin_user:
                await callback.message.answer("❌ شما دسترسی ندارید.", parse_mode="HTML")
                return

            plan = db.query(Plan).filter(Plan.id == config.plan_id, Plan.is_active == True).first()
            if not plan:
                await callback.message.answer("❌ پلن این سرویس یافت نشد یا غیرفعال است.", parse_mode="HTML")
                return

            user_payment_state[user_id] = {
                "plan_id": plan.id,
                "plan_name": plan.name,
                "price": plan.price,
                "renew_config_id": config.id,
            }

            msg = f"♻️ تمدید سرویس \"{plan.name}\"\n\n• حجم: {plan.traffic_gb} گیگ\n• مدت: {plan.duration_days} روز\n• قیمت: {plan.price} تومان\n\nروش پرداخت را انتخاب کنید:"
            await callback.message.answer(msg, reply_markup=get_payment_method_keyboard_for_renew(plan.id, config.id), parse_mode="HTML")
        finally:
            db.close()
    
    elif data.startswith("apply_discount_"):
        payload = data.replace("apply_discount_", "")
        parts = payload.split("_")
        plan_id = int(parts[0])
        renew_config_id = int(parts[1]) if len(parts) > 1 else None
        st = user_payment_state.get(user_id, {})
        st.update({"plan_id": plan_id, "renew_config_id": renew_config_id, "step": "discount_code"})
        user_payment_state[user_id] = st
        await callback.message.answer("🎁 کد تخفیف را ارسال کنید:", parse_mode="HTML")
    
    elif data == "wallet":
        db = SessionLocal()
        try:
            user = get_user(db, str(user_id))
            if user:
                await callback.message.answer(f"💰 شارژ کیف پول\n\nموجودی فعلی شما: {user.wallet_balance} تومان\n\nبرای شارژ کیف پول، لطفاً با پشتیبانی تماس بگیرید.", parse_mode="HTML")
            else:
                await callback.message.answer(WALLET_MESSAGE.format(balance=0), parse_mode="HTML")
        finally:
            db.close()

    elif data == "profile":
        db = SessionLocal()
        try:
            user = get_user(db, str(user_id))
            if user:
                configs_count = db.query(WireGuardConfig).filter(
                    WireGuardConfig.user_telegram_id == str(user_id)
                ).count()
                active_configs = db.query(WireGuardConfig).filter(
                    WireGuardConfig.user_telegram_id == str(user_id),
                    WireGuardConfig.status == "active"
                ).count()
                joined_date = format_jalali_date(user.joined_at) if user.joined_at else "نامشخص"
                member_status = "✅ فعال" if user.is_member else "❌ غیرفعال"

                msg = (
                    f"👤 حساب کاربری\n\n"
                    f"👤 نام: {user.first_name}"
                )
                if user.username:
                    msg += f"\n📛 نام کاربری: @{user.username}"

                msg += (
                    f"\n\n📊 اطلاعات اکانت:\n"
                    f"• 💰 موجودی کیف پول: {user.wallet_balance:,} تومان\n"
                    f"• 🔐 تعداد کانفیگ‌ها: {configs_count}\n"
                    f"• ✅ کانفیگ‌های فعال: {active_configs}\n"
                    f"• 📅 تاریخ عضویت: {joined_date}\n"
                    f"• 📌 وضعیت عضویت: {member_status}"
                )

                if user.is_organization_customer:
                    financials = calculate_org_user_financials(db, user)
                    msg += (
                        f"\n\n🏢 اطلاعات سازمانی (فقط خواندنی):\n"
                        f"• 📊 مجموع ترافیک لینک‌های فعال: {financials['total_traffic_gb']:.2f} GB\n"
                        f"• 💰 هزینه هر گیگ: {financials['price_per_gb']:,} تومان\n"
                        f"• 🧾 مبلغ بدهکاری: {financials['debt_amount']:,} تومان\n"
                        f"• 🕓 زمان آخرین تسویه: {financials['last_settlement']}"
                    )

                await callback.message.answer(msg, parse_mode="HTML")
            else:
                await callback.message.answer("❌ کاربر یافت نشد.", parse_mode="HTML")
        finally:
            db.close()

    # === ADMIN CALLBACKS ===
    elif data == "admin":
        pending_panel = load_pending_panel()
        await callback.message.answer(ADMIN_MESSAGE, reply_markup=get_admin_keyboard(pending_panel), parse_mode="HTML")
    
    elif data == "admin_panels":
        pending_panel = load_pending_panel()
        await callback.message.answer(PANELS_MESSAGE, reply_markup=get_panels_keyboard(pending_panel), parse_mode="HTML")

    elif data == "admin_representatives":
        db = SessionLocal()
        try:
            reps = db.query(Representative).order_by(Representative.created_at.desc()).all()
            await callback.message.answer(
                "🤝 مدیریت نمایندگی‌ها\n\nلیست نمایندگی‌ها را از پایین مدیریت کنید:",
                reply_markup=get_representatives_keyboard(reps),
                parse_mode="HTML"
            )
        finally:
            db.close()

    elif data == "rep_add":
        admin_representative_state[user_id] = {"step": "name"}
        await callback.message.answer("نام نمایندگی را وارد کنید:", parse_mode="HTML")

    elif data.startswith("rep_view_"):
        rep_id = int(data.split("_")[-1])
        db = SessionLocal()
        try:
            rep = db.query(Representative).filter(Representative.id == rep_id).first()
            if not rep:
                await callback.message.answer("❌ نمایندگی یافت نشد.", parse_mode="HTML")
                return

            configs_count = db.query(WireGuardConfig).filter(WireGuardConfig.representative_id == rep.id).count()
            payments_total = db.query(PaymentReceipt).filter(PaymentReceipt.representative_id == rep.id, PaymentReceipt.status == "approved").all()
            dynamic_sales = sum(r.amount or 0 for r in payments_total)
            traffic_rows = db.query(WireGuardConfig).filter(WireGuardConfig.representative_id == rep.id).all()
            dynamic_traffic = sum((c.cumulative_rx_bytes or 0) + (c.cumulative_tx_bytes or 0) for c in traffic_rows)

            total_configs = max(rep.total_configs or 0, configs_count)
            total_sales = max(rep.total_sales_amount or 0, dynamic_sales)
            total_traffic = max(rep.total_traffic_bytes or 0, dynamic_traffic)

            msg = (
                f"🤝 نمایندگی: {rep.name}\n"
                f"• وضعیت: {'🟢 فعال' if rep.is_active else '🔴 غیرفعال'}\n"
                f"• کانال: {rep.channel_id}\n"
                f"• ادمین نماینده: {rep.admin_telegram_id}\n"
                f"• تعداد کانفیگ‌ها: {total_configs}\n"
                f"• ترافیک مصرفی: {format_traffic(total_traffic)}\n"
                f"• مجموع هزینه‌ها: {total_sales:,} تومان\n"
                f"• کانتینر: {rep.docker_container_name or '-'}"
            )
            await callback.message.answer(msg, reply_markup=get_representative_action_keyboard(rep.id, rep.is_active), parse_mode="HTML")
        finally:
            db.close()

    elif data.startswith("rep_toggle_"):
        rep_id = int(data.split("_")[-1])
        db = SessionLocal()
        try:
            rep = db.query(Representative).filter(Representative.id == rep_id).first()
            if not rep:
                await callback.message.answer("❌ نمایندگی یافت نشد.", parse_mode="HTML")
                return

            if rep.is_active:
                ok, output = stop_representative_container(rep.docker_container_name)
                rep.is_active = False
                status = "⏸️ نمایندگی غیرفعال شد." if ok else "⚠️ وضعیت ذخیره شد ولی توقف کانتینر خطا داشت."
            else:
                ok, output = start_representative_container(rep)
                rep.is_active = ok
                status = "▶️ نمایندگی فعال شد." if ok else "⚠️ اجرای کانتینر موفق نبود."

            db.commit()
            await callback.message.answer(f"{status}\n{output[:400]}", parse_mode="HTML")
        finally:
            db.close()

    elif data.startswith("rep_delete_"):
        rep_id = int(data.split("_")[-1])
        db = SessionLocal()
        try:
            rep = db.query(Representative).filter(Representative.id == rep_id).first()
            if not rep:
                await callback.message.answer("❌ نمایندگی یافت نشد.", parse_mode="HTML")
                return

            if rep.docker_container_name:
                stop_representative_container(rep.docker_container_name)

            db.delete(rep)
            db.commit()
            await callback.message.answer("✅ نمایندگی حذف شد.", parse_mode="HTML")
        finally:
            db.close()
    
    elif data == "admin_pending_panel":
        pending = load_pending_panel()
        if not pending:
            await callback.message.answer("❌ درخواست پنل جدیدی وجود ندارد.", parse_mode="HTML")
            return
        msg = f"🔔 درخواست ثبت پنل جدید\n\n📍 اطلاعات پنل:\n• نام: {pending.get('name', 'Unknown')}\n• آی پی: {pending.get('ip', 'Unknown')}\n• لوکیشن: {pending.get('location', 'Unknown')}\n• پورت: {pending.get('port', 'Unknown')}\n• مسیر: {pending.get('path', '/')}\n\n📊 اطلاعات سیستم:\n• هاست نیم: {pending.get('system_info', {}).get('hostname', 'Unknown')}\n• سیستم عامل: {pending.get('system_info', {}).get('os', 'Unknown')}"
        await callback.message.answer(msg, reply_markup=get_pending_panel_keyboard(), parse_mode="HTML")
    
    elif data == "panel_details":
        pending = load_pending_panel()
        if not pending:
            await callback.message.answer("❌ درخواست پنل جدیدی وجود ندارد.", parse_mode="HTML")
            return
        msg = f"📋 جزئیات کامل پنل\n\n• نام: {pending.get('name', 'Unknown')}\n• آی پی: {pending.get('ip', 'Unknown')}\n• آی پی محلی: {pending.get('local_ip', 'Unknown')}\n• لوکیشن: {pending.get('location', 'Unknown')}\n• پورت: {pending.get('port', 'Unknown')}\n• مسیر: {pending.get('path', '/')}\n• نام کاربری: {pending.get('username', 'Unknown')}\n• رمز عبور: {pending.get('password', 'Unknown')}\n• نسخه X-UI: {pending.get('xui_version', 'Unknown')}\n• زمان: {pending.get('timestamp', 'Unknown')}"
        await callback.message.answer(msg, reply_markup=get_pending_panel_keyboard(), parse_mode="HTML")
    
    elif data == "panel_approve":
        pending = load_pending_panel()
        if not pending:
            await callback.message.answer("❌ درخواست پنل جدیدی وجود ندارد.", parse_mode="HTML")
            return
        db = SessionLocal()
        try:
            panel = Panel(name=pending.get('name', 'Unnamed'), ip_address=pending.get('ip', ''), local_ip=pending.get('local_ip', ''),
                        location=pending.get('location', ''), port=pending.get('port', 2053), path=pending.get('path', '/'),
                        api_username=pending.get('username', ''), api_password=pending.get('password', ''),
                        xui_version=pending.get('xui_version', ''), system_info=json.dumps(pending.get('system_info', {})),
                        status='approved', approved_at=datetime.utcnow())
            db.add(panel)
            db.commit()
            delete_pending_panel()
            await callback.message.answer("✅ پنل با موفقیت تایید و ذخیره شد!", parse_mode="HTML")
            pending_panel = load_pending_panel()
            await callback.message.answer(PANELS_MESSAGE, reply_markup=get_panels_keyboard(pending_panel), parse_mode="HTML")
        except Exception as e:
            await callback.message.answer(f"❌ خطا در ذخیره: {str(e)}", parse_mode="HTML")
        finally:
            db.close()
    
    elif data == "panel_reject":
        delete_pending_panel()
        await callback.message.answer("❌ درخواست پنل رد شد.", parse_mode="HTML")
        pending_panel = load_pending_panel()
        await callback.message.answer(PANELS_MESSAGE, reply_markup=get_panels_keyboard(pending_panel), parse_mode="HTML")
    
    elif data == "panel_list":
        db = SessionLocal()
        try:
            panels = db.query(Panel).filter(Panel.status == "approved").all()
            if panels:
                for p in panels:
                    msg = f"📋 {p.name}\n\n📍 لوکیشن: {p.location}\n🌐 آی پی: {p.ip_address}:{p.port}\n📁 مسیر: {p.path}\n👤 نام کاربری: {p.api_username}"
                    await callback.message.answer(msg, parse_mode="HTML")
            else:
                await callback.message.answer("❌ پنل تایید شده‌ای یافت نشد.", parse_mode="HTML")
        finally:
            db.close()
    
    elif data == "admin_search_user":
        admin_user_search_state[user_id] = {"active": True}
        await callback.message.answer(SEARCH_USER_MESSAGE, parse_mode="HTML")

    elif data.startswith("admin_user_") and not data.startswith((
        "admin_user_configs_",
        "admin_user_block_toggle_",
        "admin_user_org_toggle_",
        "admin_user_org_total_traffic_",
        "admin_user_org_price_",
        "admin_user_org_debt_",
        "admin_user_org_last_settlement_",
        "admin_user_org_settle_",
        "admin_user_wallet_actions_",
        "admin_user_finance_",
    )):
        target_user_id = int(data.replace("admin_user_", ""))
        db = SessionLocal()
        try:
            user_obj = db.query(User).filter(User.id == target_user_id).first()
            if not user_obj:
                await callback.message.answer("❌ کاربر یافت نشد.", parse_mode="HTML")
                return
            msg, keyboard = get_admin_user_manage_view(db, user_obj)
            await callback.message.answer(msg, reply_markup=keyboard, parse_mode="HTML")
        finally:
            db.close()

    elif data.startswith("admin_user_block_toggle_"):
        target_user_id = int(data.replace("admin_user_block_toggle_", ""))
        db = SessionLocal()
        try:
            user_obj = db.query(User).filter(User.id == target_user_id).first()
            if not user_obj:
                await callback.message.answer("❌ کاربر یافت نشد.", parse_mode="HTML")
                return
            user_obj.is_blocked = not bool(user_obj.is_blocked)
            db.commit()
            state_text = "مسدود شد" if user_obj.is_blocked else "از مسدودی خارج شد"
            await callback.message.answer(f"✅ کاربر با موفقیت {state_text}.", parse_mode="HTML")
            msg, keyboard = get_admin_user_manage_view(db, user_obj)
            await callback.message.answer(msg, reply_markup=keyboard, parse_mode="HTML")
        finally:
            db.close()

    elif data.startswith("admin_user_org_toggle_"):
        target_user_id = int(data.replace("admin_user_org_toggle_", ""))
        db = SessionLocal()
        try:
            user_obj = db.query(User).filter(User.id == target_user_id).first()
            if not user_obj:
                await callback.message.answer("❌ کاربر یافت نشد.", parse_mode="HTML")
                return
            user_obj.is_organization_customer = not bool(user_obj.is_organization_customer)
            if user_obj.org_price_per_gb is None:
                user_obj.org_price_per_gb = 3000
            db.commit()
            state_text = "مشتری سازمانی" if user_obj.is_organization_customer else "مشتری عادی"
            await callback.message.answer(f"✅ نوع مشتری با موفقیت به «{state_text}» تغییر کرد.", parse_mode="HTML")
            msg, keyboard = get_admin_user_manage_view(db, user_obj)
            await callback.message.answer(msg, reply_markup=keyboard, parse_mode="HTML")
        finally:
            db.close()


    elif data.startswith("admin_user_wallet_actions_"):
        target_user_id = int(data.replace("admin_user_wallet_actions_", ""))
        db = SessionLocal()
        try:
            user_obj = db.query(User).filter(User.id == target_user_id).first()
            if not user_obj:
                await callback.message.answer("❌ کاربر یافت نشد.", parse_mode="HTML")
                return
            msg, keyboard = get_admin_user_manage_view(db, user_obj, show_wallet_actions=True)
            await callback.message.answer(msg, reply_markup=keyboard, parse_mode="HTML")
        finally:
            db.close()

    elif data.startswith("admin_user_finance_"):
        target_user_id = int(data.replace("admin_user_finance_", ""))
        db = SessionLocal()
        try:
            user_obj = db.query(User).filter(User.id == target_user_id).first()
            if not user_obj:
                await callback.message.answer("❌ کاربر یافت نشد.", parse_mode="HTML")
                return
            msg, keyboard = get_admin_user_manage_view(db, user_obj, show_finance_panel=True)
            await callback.message.answer(msg, reply_markup=keyboard, parse_mode="HTML")
        finally:
            db.close()
    elif data.startswith("admin_user_org_total_traffic_"):
        target_user_id = int(data.replace("admin_user_org_total_traffic_", ""))
        db = SessionLocal()
        try:
            user_obj = db.query(User).filter(User.id == target_user_id).first()
            if not user_obj or not user_obj.is_organization_customer:
                await callback.answer("این کاربر مشتری سازمانی نیست.", show_alert=True)
                return
            financials = calculate_org_user_financials(db, user_obj)
            await callback.answer(f"مجموع ترافیک فعال: {financials['total_traffic_gb']:.2f} GB", show_alert=True)
        finally:
            db.close()

    elif data.startswith("admin_user_org_price_"):
        target_user_id = int(data.replace("admin_user_org_price_", ""))
        db = SessionLocal()
        try:
            user_obj = db.query(User).filter(User.id == target_user_id).first()
            if not user_obj or not user_obj.is_organization_customer:
                await callback.answer("این کاربر مشتری سازمانی نیست.", show_alert=True)
                return
            await callback.answer(f"هزینه هر گیگ: {(user_obj.org_price_per_gb or 0):,} تومان", show_alert=True)
        finally:
            db.close()

    elif data.startswith("admin_user_org_debt_"):
        target_user_id = int(data.replace("admin_user_org_debt_", ""))
        db = SessionLocal()
        try:
            user_obj = db.query(User).filter(User.id == target_user_id).first()
            if not user_obj or not user_obj.is_organization_customer:
                await callback.answer("این کاربر مشتری سازمانی نیست.", show_alert=True)
                return
            financials = calculate_org_user_financials(db, user_obj)
            await callback.answer(f"مبلغ بدهکاری: {financials['debt_amount']:,} تومان", show_alert=True)
        finally:
            db.close()

    elif data.startswith("admin_user_org_last_settlement_"):
        target_user_id = int(data.replace("admin_user_org_last_settlement_", ""))
        db = SessionLocal()
        try:
            user_obj = db.query(User).filter(User.id == target_user_id).first()
            if not user_obj or not user_obj.is_organization_customer:
                await callback.answer("این کاربر مشتری سازمانی نیست.", show_alert=True)
                return
            last_settlement = format_jalali_date(user_obj.org_last_settlement_at) if user_obj.org_last_settlement_at else "ثبت نشده"
            await callback.answer(f"آخرین تسویه: {last_settlement}", show_alert=True)
        finally:
            db.close()

    elif data.startswith("admin_user_org_settle_"):
        target_user_id = int(data.replace("admin_user_org_settle_", ""))
        db = SessionLocal()
        try:
            user_obj = db.query(User).filter(User.id == target_user_id).first()
            if not user_obj or not user_obj.is_organization_customer:
                await callback.answer("این کاربر مشتری سازمانی نیست.", show_alert=True)
                return
            active_configs = db.query(WireGuardConfig).filter(
                WireGuardConfig.user_telegram_id == user_obj.telegram_id,
                WireGuardConfig.status == "active"
            ).all()
            for cfg in active_configs:
                cfg.cumulative_rx_bytes = 0
                cfg.cumulative_tx_bytes = 0
                cfg.last_rx_counter = 0
                cfg.last_tx_counter = 0
                cfg.counter_reset_flag = True
            user_obj.org_last_settlement_at = datetime.utcnow()
            db.commit()
            await callback.message.answer("✅ تسویه حساب انجام شد و مصرف لینک‌های فعال صفر شد.", parse_mode="HTML")
            msg, keyboard = get_admin_user_manage_view(db, user_obj, show_finance_panel=True)
            await callback.message.answer(msg, reply_markup=keyboard, parse_mode="HTML")
        finally:
            db.close()

    elif data.startswith("admin_user_configs_"):
        target_user_id = int(data.replace("admin_user_configs_", ""))
        db = SessionLocal()
        try:
            user_obj = db.query(User).filter(User.id == target_user_id).first()
            if not user_obj:
                await callback.message.answer("❌ کاربر یافت نشد.", parse_mode="HTML")
                return
            configs = db.query(WireGuardConfig).filter(
                WireGuardConfig.user_telegram_id == user_obj.telegram_id
            ).order_by(WireGuardConfig.created_at.desc()).all()
            
            if configs:
                await callback.message.answer(
                    f"🔗 کانفیگ‌های کاربر {user_obj.first_name or ''}",
                    reply_markup=get_admin_user_configs_keyboard(user_obj.id, configs),
                    parse_mode="HTML"
                )
            else:
                await callback.message.answer("❌ این کاربر کانفیگی ندارد.", parse_mode="HTML")
        finally:
            db.close()

    elif data.startswith("admin_cfg_view_"):
        config_id = int(data.replace("admin_cfg_view_", ""))
        db = SessionLocal()
        try:
            config = db.query(WireGuardConfig).filter(WireGuardConfig.id == config_id).first()
            if not config:
                await callback.message.answer("❌ کانفیگ یافت نشد.", parse_mode="HTML")
                return

            plan = None
            plan_traffic_bytes = 0
            if config.plan_id:
                plan = db.query(Plan).filter(Plan.id == config.plan_id).first()
                if plan:
                    plan_traffic_bytes = (plan.traffic_gb or 0) * (1024 ** 3)

            consumed_bytes = config.cumulative_rx_bytes or 0
            remaining_bytes = max(plan_traffic_bytes - consumed_bytes, 0) if plan_traffic_bytes else 0
            expires_at = config.expires_at
            if not expires_at and plan and plan.duration_days:
                expires_at = config.created_at + timedelta(days=plan.duration_days)

            now = datetime.utcnow()
            is_expired_by_date = bool(expires_at and expires_at <= now)
            is_expired_by_traffic = bool(plan_traffic_bytes and remaining_bytes <= 0)
            is_disabled = config.status in ["expired", "revoked", "disabled"]
            can_renew = bool(config.plan_id and (is_expired_by_date or is_expired_by_traffic or is_disabled))

            status_text = "🔴 غیرفعال" if config.status != "active" else "🟢 فعال"
            
            msg = (
                f"📋 جزئیات کانفیگ (مدیریت)\n\n"
                f"• کاربر: {config.user_telegram_id}\n"
                f"• پلن: {config.plan_name or 'نامشخص'}\n"
                f"• آی پی: {config.client_ip}\n"
                f"• تاریخ خرید: {format_jalali_date(config.created_at)}\n"
                f"• تاریخ انقضا: {format_jalali_date(expires_at)}\n"
                f"• وضعیت: {status_text}\n"
                f"• حجم مصرفی: {format_traffic_size(consumed_bytes)}\n"
                f"• حجم دریافتی (RX): {format_traffic_size(config.cumulative_rx_bytes or 0)}\n"
                f"• حجم ارسالی (TX): {format_traffic_size(config.cumulative_tx_bytes or 0)}\n"
                f"• حجم باقی‌مانده: {format_traffic_size(remaining_bytes) if plan_traffic_bytes else 'نامحدود/نامشخص'}"
            )
            await callback.message.answer(
                msg,
                reply_markup=get_admin_config_detail_keyboard(config.id, can_renew=can_renew),
                parse_mode="HTML"
            )
        finally:
            db.close()

    elif data.startswith("admin_cfg_disable_"):
        if not is_admin(user_id):
            await callback.answer("❌ دسترسی ندارید.", show_alert=True)
            return
        config_id = int(data.replace("admin_cfg_disable_", ""))
        db = SessionLocal()
        try:
            config = db.query(WireGuardConfig).filter(WireGuardConfig.id == config_id).first()
            if not config:
                await callback.message.answer("❌ کانفیگ یافت نشد.", parse_mode="HTML")
                return
            
            # Disable in MikroTik
            try:
                import wireguard
                wireguard.disable_wireguard_peer(
                    mikrotik_host=MIKROTIK_HOST,
                    mikrotik_user=MIKROTIK_USER,
                    mikrotik_pass=MIKROTIK_PASS,
                    mikrotik_port=MIKROTIK_PORT,
                    wg_interface=WG_INTERFACE,
                    client_ip=config.client_ip
                )
            except Exception as e:
                print(f"MikroTik disable error: {e}")
            
            config.status = "disabled"
            db.commit()
            await callback.message.answer("✅ کانفیگ غیرفعال شد.", parse_mode="HTML")
            
            # Show config detail again
            msg = (
                f"📋 جزئیات کانفیگ (مدیریت)\n\n"
                f"• کاربر: {config.user_telegram_id}\n"
                f"• پلن: {config.plan_name or 'نامشخص'}\n"
                f"• آی پی: {config.client_ip}\n"
                f"• وضعیت: 🔴 غیرفعال"
            )
            await callback.message.answer(
                msg,
                reply_markup=get_admin_config_detail_keyboard(config.id, can_renew=True),
                parse_mode="HTML"
            )
        finally:
            db.close()

    elif data.startswith("admin_cfg_delete_"):
        if not is_admin(user_id):
            await callback.answer("❌ دسترسی ندارید.", show_alert=True)
            return
        config_id = int(data.replace("admin_cfg_delete_", ""))
        db = SessionLocal()
        try:
            config = db.query(WireGuardConfig).filter(WireGuardConfig.id == config_id).first()
            if not config:
                await callback.message.answer("❌ کانفیگ یافت نشد.", parse_mode="HTML")
                return
            
            await callback.message.answer(
                f"⚠️ آیا از حذف کانفیگ {config.client_ip} اطمینان دارید؟\n\nاین عملیات غیرقابل بازگشت است و کانفیگ از میکروتیک حذف می‌شود.",
                reply_markup=get_admin_config_confirm_delete_keyboard(config.id),
                parse_mode="HTML"
            )
        finally:
            db.close()

    elif data.startswith("admin_cfg_delete_confirm_"):
        if not is_admin(user_id):
            await callback.answer("❌ دسترسی ندارید.", show_alert=True)
            return
        config_id = int(data.replace("admin_cfg_delete_confirm_", ""))
        db = SessionLocal()
        try:
            config = db.query(WireGuardConfig).filter(WireGuardConfig.id == config_id).first()
            if not config:
                await callback.message.answer("❌ کانفیگ یافت نشد.", parse_mode="HTML")
                return
            
            client_ip = config.client_ip
            user_tg_id = config.user_telegram_id
            
            # Delete from MikroTik
            try:
                import wireguard
                wireguard.delete_wireguard_peer(
                    mikrotik_host=MIKROTIK_HOST,
                    mikrotik_user=MIKROTIK_USER,
                    mikrotik_pass=MIKROTIK_PASS,
                    mikrotik_port=MIKROTIK_PORT,
                    wg_interface=WG_INTERFACE,
                    client_ip=client_ip
                )
            except Exception as e:
                print(f"MikroTik delete error: {e}")
            
            # Delete from database
            db.delete(config)
            db.commit()
            
            await callback.message.answer(
                f"✅ کانفیگ {client_ip} حذف شد.",
                parse_mode="HTML"
            )
        finally:
            db.close()

    elif data.startswith("wallet_inc_") or data.startswith("wallet_dec_"):
        if not is_admin(user_id):
            await callback.answer("❌ دسترسی ندارید.", show_alert=True)
            return
        target_user_id = int(data.split("_")[-1])
        admin_wallet_adjust_state[user_id] = {
            "target_user_id": target_user_id,
            "op": "inc" if data.startswith("wallet_inc_") else "dec",
        }
        await callback.message.answer("مقدار را وارد کنید:", parse_mode="HTML")

    elif data == "admin_discount_create":
        if not is_admin(user_id):
            await callback.answer("❌ دسترسی ندارید.", show_alert=True)
            return
        admin_discount_state[user_id] = {"step": "code"}
        await callback.message.answer("کد تخفیف را وارد کنید (مثال: NEWYEAR):", parse_mode="HTML")
    
    elif data == "admin_service_types":
        db = SessionLocal()
        try:
            rows = db.query(ServiceType).order_by(ServiceType.id.asc()).all()
            await callback.message.answer("🧩 مدیریت انواع سرویس", reply_markup=get_service_types_keyboard(rows), parse_mode="HTML")
        finally:
            db.close()

    # === TUTORIAL HANDLERS ===
    elif data == "admin_tutorials":
        db = SessionLocal()
        try:
            service_types = db.query(ServiceType).filter(ServiceType.is_active == True).order_by(ServiceType.id.asc()).all()
            if service_types:
                await callback.message.answer(
                    "📚 مدیریت آموزش\n\nنوع سرویس را برای ویرایش آموزش انتخاب کنید:",
                    reply_markup=get_service_type_picker_keyboard(service_types, "admin_tutorial_edit_"),
                    parse_mode="HTML"
                )
            else:
                await callback.message.answer("❌ هیچ نوع سرویسی یافت نشد.", parse_mode="HTML")
        finally:
            db.close()

    elif data.startswith("admin_tutorial_edit_"):
        service_type_id = int(data.split("_")[-1])
        db = SessionLocal()
        try:
            service_type = db.query(ServiceType).filter(ServiceType.id == service_type_id).first()
            if not service_type:
                await callback.message.answer("❌ نوع سرویس یافت نشد.", parse_mode="HTML")
                return
            
            tutorial = db.query(ServiceTutorial).filter(
                ServiceTutorial.service_type_id == service_type_id,
                ServiceTutorial.is_active == True
            ).first()
            
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            if tutorial:
                # Show existing tutorial with option to edit
                msg = f"📚 آموزش {service_type.name}\n\n"
                if tutorial.description:
                    msg += f"متن: {tutorial.description[:200]}...\n"
                if tutorial.media_type:
                    msg += f"رسانه: {'عکس' if tutorial.media_type == 'photo' else 'ویدیو'} 📎"
                
                await callback.message.answer(
                    msg,
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="✏️ ویرایش آموزش", callback_data=f"admin_tutorial_create_{service_type_id}")],
                        [InlineKeyboardButton(text="🗑️ حذف آموزش", callback_data=f"admin_tutorial_delete_{service_type_id}")],
                        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_tutorials")]
                    ]),
                    parse_mode="HTML"
                )
            else:
                await callback.message.answer(
                    f"📚 آموزش {service_type.name}\n\nآموزشی تعریف نشده است.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="➕ افزودن آموزش", callback_data=f"admin_tutorial_create_{service_type_id}")],
                        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_tutorials")]
                    ]),
                    parse_mode="HTML"
                )
        finally:
            db.close()

    elif data.startswith("admin_tutorial_create_"):
        service_type_id = int(data.split("_")[-1])
        db = SessionLocal()
        try:
            service_type = db.query(ServiceType).filter(ServiceType.id == service_type_id).first()
            if not service_type:
                await callback.message.answer("❌ نوع سرویس یافت نشد.", parse_mode="HTML")
                return
            
            # Start tutorial creation flow
            admin_tutorial_state[user_id] = {
                "service_type_id": service_type_id,
                "step": "title"
            }
            
            await callback.message.answer(
                f"📝 ایجاد آموزش برای {service_type.name}\n\n"
                "لطفاً عنوان آموزش را وارد کنید:",
                parse_mode="HTML"
            )
        finally:
            db.close()

    elif data.startswith("admin_tutorial_delete_"):
        service_type_id = int(data.split("_")[-1])
        db = SessionLocal()
        try:
            tutorial = db.query(ServiceTutorial).filter(
                ServiceTutorial.service_type_id == service_type_id
            ).first()
            
            if tutorial:
                db.delete(tutorial)
                db.commit()
                await callback.message.answer("✅ آموزش حذف شد.", parse_mode="HTML")
            else:
                await callback.message.answer("❌ آموزش یافت نشد.", parse_mode="HTML")
            
            # Show service types again
            service_types = db.query(ServiceType).filter(ServiceType.is_active == True).order_by(ServiceType.id.asc()).all()
            await callback.message.answer(
                "📚 مدیریت آموزش\n\nنوع سرویس را انتخاب کنید:",
                reply_markup=get_service_type_picker_keyboard(service_types, "admin_tutorial_edit_"),
                parse_mode="HTML"
            )
        finally:
            db.close()

    elif data.startswith("admin_tutorial_skip_media_"):
        service_type_id = int(data.split("_")[-1])
        if user_id not in admin_tutorial_state:
            await callback.message.answer("❌ عملیات منقضی شده است.", parse_mode="HTML")
            return
        
        state = admin_tutorial_state[user_id]
        if state.get("service_type_id") != service_type_id:
            await callback.message.answer("❌ عملیات نامعتبر است.", parse_mode="HTML")
            return
        
        db = SessionLocal()
        try:
            # Check if tutorial exists and update, or create new
            existing = db.query(ServiceTutorial).filter(
                ServiceTutorial.service_type_id == service_type_id
            ).first()
            
            if existing:
                existing.title = state.get("title", "")
                existing.description = state.get("description", "")
                existing.media_type = None
                existing.media_file_id = None
                existing.updated_at = datetime.utcnow()
            else:
                tutorial = ServiceTutorial(
                    service_type_id=service_type_id,
                    title=state.get("title", ""),
                    description=state.get("description", ""),
                    media_type=None,
                    media_file_id=None,
                    is_active=True
                )
                db.add(tutorial)
            
            db.commit()
            await callback.message.answer("✅ آموزش ذخیره شد!\n(بدون رسانه)", parse_mode="HTML")
        except Exception as e:
            await callback.message.answer(f"❌ خطا: {e}", parse_mode="HTML")
        finally:
            db.close()
            del admin_tutorial_state[user_id]

    # === USER TUTORIAL VIEW ===
    elif data == "user_tutorials":
        db = SessionLocal()
        try:
            service_types = db.query(ServiceType).filter(ServiceType.is_active == True).order_by(ServiceType.id.asc()).all()
            if service_types:
                await callback.message.answer(
                    "📚 آموزش\n\nنوع سرویس را انتخاب کنید:",
                    reply_markup=get_service_type_picker_keyboard(service_types, "user_tutorial_view_"),
                    parse_mode="HTML"
                )
            else:
                await callback.message.answer("❌ هیچ نوع سرویسی یافت نشد.", parse_mode="HTML")
        finally:
            db.close()

    elif data.startswith("user_tutorial_view_"):
        service_type_id = int(data.split("_")[-1])
        db = SessionLocal()
        try:
            service_type = db.query(ServiceType).filter(ServiceType.id == service_type_id).first()
            if not service_type:
                await callback.message.answer("❌ نوع سرویس یافت نشد.", parse_mode="HTML")
                return
            
            tutorial = db.query(ServiceTutorial).filter(
                ServiceTutorial.service_type_id == service_type_id,
                ServiceTutorial.is_active == True
            ).first()
            
            if not tutorial:
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                await callback.message.answer(
                    f"📚 آموزش {service_type.name}\n\nآموزشی یافت نشد.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="user_tutorials")]
                    ]),
                    parse_mode="HTML"
                )
                return
            
            # Send tutorial with media if available
            if tutorial.media_file_id:
                if tutorial.media_type == "photo":
                    await callback.message.answer_photo(
                        photo=tutorial.media_file_id,
                        caption=f"📚 {tutorial.title}\n\n{tutorial.description or ''}",
                        parse_mode="HTML"
                    )
                elif tutorial.media_type == "video":
                    await callback.message.answer_video(
                        video=tutorial.media_file_id,
                        caption=f"📚 {tutorial.title}\n\n{tutorial.description or ''}",
                        parse_mode="HTML"
                    )
            else:
                # No media, just send text
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                await callback.message.answer(
                    f"📚 {tutorial.title}\n\n{tutorial.description or 'بدون توضیحات'}",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="user_tutorials")]
                    ]),
                    parse_mode="HTML"
                )
        finally:
            db.close()

    elif data == "service_type_add":
        admin_service_type_state[user_id] = {"step": "name"}
        await callback.message.answer("نام نوع سرویس جدید را وارد کنید:", parse_mode="HTML")

    elif data.startswith("service_type_view_"):
        st_id = int(data.split("_")[-1])
        db = SessionLocal()
        try:
            st = db.query(ServiceType).filter(ServiceType.id == st_id).first()
            if not st:
                await callback.message.answer("❌ نوع سرویس یافت نشد.", parse_mode="HTML")
                return
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            await callback.message.answer(
                f"🧩 {st.name} ({st.code})",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🗑️ حذف", callback_data=f"service_type_delete_{st.id}")]]),
                parse_mode="HTML",
            )
        finally:
            db.close()

    elif data.startswith("service_type_delete_"):
        st_id = int(data.split("_")[-1])
        db = SessionLocal()
        try:
            st = db.query(ServiceType).filter(ServiceType.id == st_id).first()
            if not st:
                await callback.message.answer("❌ نوع سرویس یافت نشد.", parse_mode="HTML")
                return
            has_plan = db.query(Plan).filter(Plan.service_type_id == st.id).first()
            has_server = db.query(Server).filter(Server.service_type_id == st.id).first()
            if has_plan or has_server:
                await callback.message.answer("❌ ابتدا پلن‌ها و سرورهای این نوع سرویس را حذف کنید.", parse_mode="HTML")
                return
            db.delete(st)
            db.commit()
            await callback.message.answer("✅ نوع سرویس حذف شد.", parse_mode="HTML")
        finally:
            db.close()

    elif data == "admin_servers":
        db = SessionLocal()
        try:
            rows = db.query(ServiceType).filter(ServiceType.is_active == True).all()
            await callback.message.answer("🖧 مدیریت سرورها\n\nابتدا نوع سرویس را انتخاب کنید:", reply_markup=get_servers_service_type_keyboard(rows), parse_mode="HTML")
        finally:
            db.close()

    elif data.startswith("admin_servers_type_"):
        service_type_id = int(data.split("_")[-1])
        db = SessionLocal()
        try:
            servers = db.query(Server).filter(Server.service_type_id == service_type_id).all()
            await callback.message.answer("📋 لیست سرورها:", reply_markup=get_servers_keyboard(servers, service_type_id), parse_mode="HTML")
        finally:
            db.close()

    elif data.startswith("server_add_"):
        service_type_id = int(data.split("_")[-1])
        if data == "server_add_cancel":
            if user_id in admin_server_state:
                del admin_server_state[user_id]
            await callback.message.answer("❌ عملیات لغو شد.", parse_mode="HTML")
            return
        admin_server_state[user_id] = {"step": "name", "service_type_id": service_type_id}
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        await callback.message.answer(
            "نام سرور را وارد کنید:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ انصراف", callback_data="server_add_cancel")]
            ]),
            parse_mode="HTML"
        )

    elif data.startswith("server_view_"):
        server_id = int(data.split("_")[-1])
        db = SessionLocal()
        try:
            srv = db.query(Server).filter(Server.id == server_id).first()
            if not srv:
                await callback.message.answer("❌ سرور یافت نشد.", parse_mode="HTML")
                return
            used = get_server_active_config_count(db, srv.id)
            msg = (
                f"🖧 {srv.name}\n"
                f"• Host: {srv.host}\n"
                f"• API Port: {srv.api_port}\n"
                f"• ظرفیت: {used}/{srv.capacity}\n"
                f"• Interface: {srv.wg_interface or '-'}\n"
                f"• Endpoint: {srv.wg_server_endpoint or '-'}:{srv.wg_server_port or '-'}"
            )
            await callback.message.answer(msg, reply_markup=get_server_action_keyboard(srv.id, srv.service_type_id), parse_mode="HTML")
        finally:
            db.close()

    elif data.startswith("server_edit_"):
        server_id = int(data.split("_")[-1])
        admin_server_state[user_id] = {"step": "edit_capacity", "server_id": server_id}
        await callback.message.answer("ظرفیت جدید سرور را وارد کنید:", parse_mode="HTML")

    elif data.startswith("server_delete_"):
        server_id = int(data.split("_")[-1])
        db = SessionLocal()
        try:
            srv = db.query(Server).filter(Server.id == server_id).first()
            if not srv:
                await callback.message.answer("❌ سرور یافت نشد.", parse_mode="HTML")
                return
            db.query(PlanServerMap).filter(PlanServerMap.server_id == srv.id).delete()
            db.delete(srv)
            db.commit()
            await callback.message.answer("✅ سرور حذف شد.", parse_mode="HTML")
        finally:
            db.close()

    elif data == "admin_plans":
        db = SessionLocal()
        try:
            plans = db.query(Plan).all()
            await callback.message.answer(PLANS_MESSAGE, reply_markup=get_plans_keyboard(plans), parse_mode="HTML")
        finally:
            db.close()
    
    elif data == "admin_receipts":
        db = SessionLocal()
        try:
            pending_receipts = db.query(PaymentReceipt).filter(PaymentReceipt.status == "pending").all()
            if pending_receipts:
                for receipt in pending_receipts:
                    msg = f"💳 فیش پرداخت\n\n• پلن: {receipt.plan_name}\n• مبلغ: {receipt.amount} تومان\n• کاربر: {receipt.user_telegram_id}\n• تاریخ: {receipt.created_at}"
                    await callback.message.answer(msg, reply_markup=get_receipt_action_keyboard(receipt.id), parse_mode="HTML")
            else:
                await callback.message.answer("❌ فیش پرداخت در انتظار تاییدی وجود ندارد.", parse_mode="HTML")
        finally:
            db.close()
    
    # === CREATE ACCOUNT HANDLERS ===
    elif data == "admin_create_account":
        db = SessionLocal()
        try:
            plans = db.query(Plan).filter(Plan.is_active == True).all()
            if plans:
                await callback.message.answer("🔗 ساخت اکانت وایرگارد\n\nیکی از پلن‌های زیر را انتخاب کنید و یا پلن دلخواه بسازید:", reply_markup=get_create_account_keyboard(plans), parse_mode="HTML")
            else:
                await callback.message.answer("❌ پلن فعالی وجود ندارد. می‌توانید پلن دلخواه بسازید.", reply_markup=get_create_account_keyboard([]), parse_mode="HTML")
        finally:
            db.close()
    
    elif data.startswith("create_acc_plan_"):
        plan_id = int(data.split("_")[-1])
        db = SessionLocal()
        try:
            plan = db.query(Plan).filter(Plan.id == plan_id, Plan.is_active == True).first()
            if not plan:
                await callback.message.answer("❌ پلن یافت نشد یا غیرفعال است.", parse_mode="HTML")
                return
            available_servers = get_available_servers_for_plan(db, plan.id)
            if not available_servers:
                await callback.message.answer("❌ ظرفیت سرورهای این پلن تکمیل است.", parse_mode="HTML")
                return
            await callback.message.answer("سرور را برای ساخت اکانت انتخاب کنید:", reply_markup=get_plan_server_select_keyboard(available_servers, f"create_acc_server_{plan.id}_"), parse_mode="HTML")
        finally:
            db.close()

    elif data.startswith("create_acc_server_"):
        parts = data.split("_")
        plan_id = int(parts[3])
        server_id = int(parts[4])
        db = SessionLocal()
        try:
            plan = db.query(Plan).filter(Plan.id == plan_id, Plan.is_active == True).first()
            server = db.query(Server).filter(Server.id == server_id, Server.is_active == True).first()
            if not plan or not server:
                await callback.message.answer("❌ پلن/سرور نامعتبر است.", parse_mode="HTML")
                return
            import wireguard
            wg_result = wireguard.create_wireguard_account(**build_wg_kwargs(server, str(user_id), plan, plan.name, plan.duration_days))
            if wg_result.get("success"):
                await callback.message.answer(f"✅ اکانت روی سرور {server.name} ایجاد شد.", parse_mode="HTML")
                if wg_result.get("config"):
                    await send_wireguard_config_file(callback.message, wg_result.get("config"), caption="📄 فایل کانفیگ WireGuard")
                if wg_result.get("qr_code"):
                    await send_qr_code(callback.message, wg_result.get("qr_code"), f"QR Code - {plan.name}")
            else:
                await callback.message.answer(f"❌ خطا در ایجاد اکانت: {wg_result.get('error', 'خطای نامشخص')}", parse_mode="HTML")
        finally:
            db.close()

    elif data == "create_acc_custom":
        # Start custom plan flow - ask for name first
        admin_create_account_state[user_id] = {"step": "name"}
        await callback.message.answer(
            "📝 ساخت پلن دلخواه\n\nلطفاً نام اکانت را وارد کنید:\n(مثلاً: اکانت شخصی یا نام کاربر)",
            parse_mode="HTML"
        )
    
    # === PLAN CALLBACKS ===
    elif data == "plan_list":
        db = SessionLocal()
        try:
            plans = db.query(Plan).all()
            if plans:
                await callback.message.answer("📋 لیست پلن‌ها:", reply_markup=get_plan_list_keyboard(plans), parse_mode="HTML")
            else:
                await callback.message.answer("❌ پلنی یافت نشد.\n\nبرای ایجاد پلن جدید، دکمه «➕ پلن جدید» را بزنید.", parse_mode="HTML")
        finally:
            db.close()
    
    elif data == "plan_test_account":
        db = SessionLocal()
        try:
            test_plan = db.query(Plan).filter(Plan.name == TEST_ACCOUNT_PLAN_NAME).first()
            if test_plan:
                status = "✅ فعال" if test_plan.is_active else "❌ غیرفعال"
                desc = test_plan.description if test_plan.description else "ندارد"
                msg = (
                    "🧪 اطلاعات اکانت تست\n\n"
                    f"• نام: {test_plan.name}\n"
                    f"• مدت: {test_plan.duration_days} روز\n"
                    f"• ترافیک: {test_plan.traffic_gb} گیگابایت\n"
                    f"• قیمت: {test_plan.price} تومان\n"
                    f"• وضعیت: {status}\n"
                    f"• توضیحات: {desc}"
                )
            else:
                msg = "🧪 اکانت تست هنوز تعریف نشده است."
            await callback.message.answer(msg, reply_markup=get_test_account_keyboard(bool(test_plan)), parse_mode="HTML")
        finally:
            db.close()

    elif data == "plan_test_account_edit":
        admin_plan_state[user_id] = {"action": "test_account_setup", "step": "days"}
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        await callback.message.answer(
            "🧪 ویرایش اکانت تست\n\nلطفاً تعداد روز اکانت تست را وارد کنید:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 انصراف", callback_data="admin_plans")]
            ]),
            parse_mode="HTML"
        )

    elif data == "plan_create":
        admin_plan_state[user_id] = {"action": "create", "plan_id": "new", "step": "name", "data": {}}
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        await callback.message.answer(
            "➕ ایجاد پلن جدید\n\n"
            "لطفاً اطلاعات پلن را مرحله‌به‌مرحله وارد کنید.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 انصراف", callback_data="admin_plans")]
            ]),
            parse_mode="HTML"
        )
        await callback.message.answer(get_plan_field_prompt("name"), parse_mode="HTML")
    
    elif data.startswith("plan_view_"):
        plan_id = int(data.split("_")[-1])
        db = SessionLocal()
        try:
            plan = db.query(Plan).filter(Plan.id == plan_id).first()
            if plan:
                status = "✅ فعال" if plan.is_active else "❌ غیرفعال"
                desc = plan.description if plan.description else "ندارد"
                msg = f"📦 اطلاعات پلن\n\n• نام: {plan.name}\n• مدت: {plan.duration_days} روز\n• ترافیک: {plan.traffic_gb} گیگابایت\n• قیمت: {plan.price} تومان\n• وضعیت: {status}\n• توضیحات: {desc}"
                await callback.message.answer(msg, reply_markup=get_plan_action_keyboard(plan.id, plan.is_active), parse_mode="HTML")
            else:
                await callback.message.answer("❌ پلن یافت نشد.", parse_mode="HTML")
        finally:
            db.close()
    
    elif data.startswith("plan_edit_"):
        plan_id = int(data.split("_")[-1])
        db = SessionLocal()
        try:
            plan = db.query(Plan).filter(Plan.id == plan_id).first()
            if plan:
                selected_server_ids = [m.server_id for m in db.query(PlanServerMap).filter(PlanServerMap.plan_id == plan.id).all()]
                admin_plan_state[user_id] = {"action": "edit", "plan_id": plan_id, "data": {"name": plan.name, "days": str(plan.duration_days), "traffic": str(plan.traffic_gb), "price": str(plan.price), "description": plan.description or "", "service_type_id": plan.service_type_id, "server_ids": selected_server_ids}}
                msg = f"✏️ ویرایش پلن: {plan.name}\n\nمی‌توانید هر فیلدی را که می‌خواهید تغییر دهید:"
                await callback.message.answer(msg, reply_markup=get_plan_edit_keyboard(plan_id), parse_mode="HTML")
            else:
                await callback.message.answer("❌ پلن یافت نشد.", parse_mode="HTML")
        finally:
            db.close()
    
    elif data.startswith("plan_toggle_"):
        plan_id = int(data.split("_")[-1])
        db = SessionLocal()
        try:
            plan = db.query(Plan).filter(Plan.id == plan_id).first()
            if plan:
                plan.is_active = not plan.is_active
                db.commit()
                status_text = "فعال" if plan.is_active else "غیرفعال"
                await callback.message.answer(f"✅ پلن «{plan.name}» {status_text} شد.", parse_mode="HTML")
                status = "✅ فعال" if plan.is_active else "❌ غیرفعال"
                desc = plan.description if plan.description else "ندارد"
                msg = f"📦 اطلاعات پلن\n\n• نام: {plan.name}\n• مدت: {plan.duration_days} روز\n• ترافیک: {plan.traffic_gb} گیگابایت\n• قیمت: {plan.price} تومان\n• وضعیت: {status}\n• توضیحات: {desc}"
                await callback.message.answer(msg, reply_markup=get_plan_action_keyboard(plan.id, plan.is_active), parse_mode="HTML")
            else:
                await callback.message.answer("❌ پلن یافت نشد.", parse_mode="HTML")
        except Exception as e:
            await callback.message.answer(f"❌ خطا: {str(e)}", parse_mode="HTML")
        finally:
            db.close()
    
    elif data.startswith("plan_delete_"):
        plan_id = int(data.split("_")[-1])
        db = SessionLocal()
        try:
            plan = db.query(Plan).filter(Plan.id == plan_id).first()
            if plan:
                plan_name = plan.name
                db.delete(plan)
                db.commit()
                await callback.message.answer(f"✅ پلن «{plan_name}» با موفقیت حذف شد.", parse_mode="HTML")
                # Show the plans list with remaining plans
                all_plans = db.query(Plan).all()
                await callback.message.answer(PLANS_MESSAGE, reply_markup=get_plans_keyboard(all_plans), parse_mode="HTML")
            else:
                await callback.message.answer("❌ پلن یافت نشد.", parse_mode="HTML")
        except Exception as e:
            await callback.message.answer(f"❌ خطا در حذف: {str(e)}", parse_mode="HTML")
        finally:
            db.close()
    
    elif data.startswith("plan_set_name_"):
        plan_id = data.split("_")[-1]
        current_state = admin_plan_state.get(user_id, {})
        current = current_state.get("data", {}).get("name", "")
        admin_plan_state[user_id] = {"action": "create" if plan_id == "new" else "edit", "plan_id": plan_id, "field": "name", "data": current_state.get("data", {})}
        await callback.message.answer(get_plan_field_prompt("name", current), parse_mode="HTML")
    
    elif data.startswith("plan_set_days_"):
        plan_id = data.split("_")[-1]
        current_state = admin_plan_state.get(user_id, {})
        current = current_state.get("data", {}).get("days", "")
        admin_plan_state[user_id] = {"action": "create" if plan_id == "new" else "edit", "plan_id": plan_id, "field": "days", "data": current_state.get("data", {})}
        await callback.message.answer(get_plan_field_prompt("days", current), parse_mode="HTML")
    
    elif data.startswith("plan_set_traffic_"):
        plan_id = data.split("_")[-1]
        current_state = admin_plan_state.get(user_id, {})
        current = current_state.get("data", {}).get("traffic", "")
        admin_plan_state[user_id] = {"action": "create" if plan_id == "new" else "edit", "plan_id": plan_id, "field": "traffic", "data": current_state.get("data", {})}
        await callback.message.answer(get_plan_field_prompt("traffic", current), parse_mode="HTML")
    
    elif data.startswith("plan_set_price_"):
        plan_id = data.split("_")[-1]
        current_state = admin_plan_state.get(user_id, {})
        current = current_state.get("data", {}).get("price", "")
        admin_plan_state[user_id] = {"action": "create" if plan_id == "new" else "edit", "plan_id": plan_id, "field": "price", "data": current_state.get("data", {})}
        await callback.message.answer(get_plan_field_prompt("price", current), parse_mode="HTML")
    
    elif data.startswith("plan_set_desc_"):
        plan_id = data.split("_")[-1]
        current_state = admin_plan_state.get(user_id, {})
        current = current_state.get("data", {}).get("description", "")
        admin_plan_state[user_id] = {"action": "create" if plan_id == "new" else "edit", "plan_id": plan_id, "field": "description", "data": current_state.get("data", {})}
        await callback.message.answer(get_plan_field_prompt("description", current), parse_mode="HTML")
    
    elif data.startswith("plan_set_service_"):
        plan_id = data.split("_")[-1]
        db = SessionLocal()
        try:
            service_types = db.query(ServiceType).filter(ServiceType.is_active == True).all()
            await callback.message.answer("نوع سرویس پلن را انتخاب کنید:", reply_markup=get_service_type_picker_keyboard(service_types, f"plan_pick_service_{plan_id}_"), parse_mode="HTML")
        finally:
            db.close()

    elif data.startswith("plan_pick_service_"):
        parts = data.split("_")
        plan_id = parts[3]
        service_type_id = int(parts[-1])
        current_state = admin_plan_state.get(user_id, {"data": {}})
        current_state.setdefault("data", {})["service_type_id"] = service_type_id
        current_state["plan_id"] = plan_id
        current_state["action"] = "create" if plan_id == "new" else "edit"
        admin_plan_state[user_id] = current_state
        await callback.message.answer("✅ نوع سرویس ثبت شد.", parse_mode="HTML")

    elif data.startswith("plan_set_servers_"):
        plan_id = data.split("_")[-1]
        st = admin_plan_state.get(user_id, {"data": {}})
        service_type_id = st.get("data", {}).get("service_type_id")
        if not service_type_id:
            await callback.message.answer("❌ ابتدا نوع سرویس را انتخاب کنید.", parse_mode="HTML")
            return
        db = SessionLocal()
        try:
            servers = db.query(Server).filter(Server.service_type_id == service_type_id, Server.is_active == True).all()
            await callback.message.answer("سرورهای مجاز پلن را انتخاب کنید (چندتایی مجاز است).", reply_markup=get_plan_servers_picker_keyboard(servers, plan_id), parse_mode="HTML")
        finally:
            db.close()

    elif data.startswith("plan_toggle_server_"):
        _, _, _, plan_id_token, server_id_s = data.split("_", 4)
        server_id = int(server_id_s)
        st = admin_plan_state.setdefault(user_id, {"data": {}})
        selected = st.setdefault("data", {}).setdefault("server_ids", [])
        if server_id in selected:
            selected.remove(server_id)
            await callback.answer("سرور حذف شد")
        else:
            selected.append(server_id)
            await callback.answer("سرور اضافه شد")

    elif data.startswith("plan_servers_done_"):
        await callback.message.answer("✅ انتخاب سرورها ذخیره شد.", parse_mode="HTML")

    elif data == "plan_save_new":
        state = admin_plan_state.get(user_id, {})
        plan_data = state.get("data", {})
        if not all([plan_data.get("name"), plan_data.get("days"), plan_data.get("traffic"), plan_data.get("price"), plan_data.get("service_type_id")]):
            await callback.message.answer("❌ لطفاً تمام فیلدهای الزامی (از جمله نوع سرویس) را تکمیل کنید.", parse_mode="HTML")
            return
        # Convert Persian/Arabic numbers to English
        days = normalize_numbers(plan_data.get("days", "0"))
        traffic = normalize_numbers(plan_data.get("traffic", "0"))
        price = normalize_numbers(plan_data.get("price", "0"))
        db = SessionLocal()
        try:
            plan = Plan(name=plan_data["name"], duration_days=int(days), traffic_gb=int(traffic),
                       price=int(price), description=plan_data.get("description", ""), is_active=True,
                       service_type_id=int(plan_data.get("service_type_id")))
            db.add(plan)
            db.commit()
            selected_servers = plan_data.get("server_ids", [])
            for sid in selected_servers:
                db.add(PlanServerMap(plan_id=plan.id, server_id=int(sid)))
            db.commit()
            if user_id in admin_plan_state:
                del admin_plan_state[user_id]
            await callback.message.answer(f"✅ پلن «{plan.name}» با موفقیت ایجاد شد!", parse_mode="HTML")
            # Show the plans list with all plans
            all_plans = db.query(Plan).all()
            await callback.message.answer(PLANS_MESSAGE, reply_markup=get_plans_keyboard(all_plans), parse_mode="HTML")
        except Exception as e:
            await callback.message.answer(f"❌ خطا در ذخیره: {str(e)}", parse_mode="HTML")
        finally:
            db.close()
    
    elif data.startswith("plan_save_") and data != "plan_save_new":
        plan_id = int(data.split("_")[-1])
        state = admin_plan_state.get(user_id, {})
        plan_data = state.get("data", {})
        if not all([plan_data.get("name"), plan_data.get("days"), plan_data.get("traffic"), plan_data.get("price"), plan_data.get("service_type_id")]):
            await callback.message.answer("❌ لطفاً تمام فیلدهای الزامی (از جمله نوع سرویس) را تکمیل کنید.", parse_mode="HTML")
            return
        # Convert Persian/Arabic numbers to English
        days = normalize_numbers(plan_data.get("days", "0"))
        traffic = normalize_numbers(plan_data.get("traffic", "0"))
        price = normalize_numbers(plan_data.get("price", "0"))
        db = SessionLocal()
        try:
            plan = db.query(Plan).filter(Plan.id == plan_id).first()
            if plan:
                plan.name = plan_data["name"]
                plan.duration_days = int(days)
                plan.traffic_gb = int(traffic)
                plan.price = int(price)
                plan.description = plan_data.get("description", "")
                plan.service_type_id = int(plan_data.get("service_type_id") or 0) or plan.service_type_id
                db.query(PlanServerMap).filter(PlanServerMap.plan_id == plan.id).delete()
                for sid in plan_data.get("server_ids", []):
                    db.add(PlanServerMap(plan_id=plan.id, server_id=int(sid)))
                db.commit()
                if user_id in admin_plan_state:
                    del admin_plan_state[user_id]
                await callback.message.answer(f"✅ پلن «{plan.name}» با موفقیت ویرایش شد!", parse_mode="HTML")
                # Show the plans list with all plans
                all_plans = db.query(Plan).all()
                await callback.message.answer(PLANS_MESSAGE, reply_markup=get_plans_keyboard(all_plans), parse_mode="HTML")
            else:
                await callback.message.answer("❌ پلن یافت نشد.", parse_mode="HTML")
        except Exception as e:
            await callback.message.answer(f"❌ خطا در ذخیره: {str(e)}", parse_mode="HTML")
        finally:
            db.close()
    
    # === PAYMENT CALLBACKS ===
    elif data.startswith("buy_plan_"):
        plan_id = int(data.split("_")[-1])
        db = SessionLocal()
        try:
            plan = db.query(Plan).filter(Plan.id == plan_id, Plan.is_active == True).first()
            if not plan:
                await callback.message.answer("❌ پلن یافت نشد یا غیرفعال است.", parse_mode="HTML")
                return
            available_servers = get_available_servers_for_plan(db, plan.id)
            if available_servers:
                user_payment_state[user_id] = {"plan_id": plan_id, "plan_name": plan.name, "price": plan.price}
                if len(available_servers) > 1:
                    await callback.message.answer("ابتدا سرور را انتخاب کنید:", reply_markup=get_plan_server_select_keyboard(available_servers, f"buy_pick_server_{plan.id}_"), parse_mode="HTML")
                    return
                user_payment_state[user_id]["server_id"] = available_servers[0].id
            else:
                await callback.message.answer("❌ ظرفیت سرورهای این پلن تکمیل است.", parse_mode="HTML")
                return

            msg = (
                f'💳 پرداخت پلن "{plan.name}"\n\n'
                f"• حجم: {plan.traffic_gb} گیگ\n"
                f"• مدت: {plan.duration_days} روز\n"
                f"• قیمت: {plan.price} تومان\n\n"
                "روش پرداخت را انتخاب کنید:"
            )
            await callback.message.answer(msg, reply_markup=get_payment_method_keyboard(plan_id), parse_mode="HTML")
        finally:
            db.close()

    elif data.startswith("buy_pick_server_"):
        parts = data.split("_")
        plan_id = int(parts[3])
        server_id = int(parts[4])
        db = SessionLocal()
        try:
            plan = db.query(Plan).filter(Plan.id == plan_id, Plan.is_active == True).first()
            if not plan:
                await callback.message.answer("❌ پلن معتبر نیست.", parse_mode="HTML")
                return
            state = user_payment_state.get(user_id, {})
            state.update({"plan_id": plan_id, "plan_name": plan.name, "price": plan.price, "server_id": server_id})
            user_payment_state[user_id] = state
            await callback.message.answer("✅ سرور انتخاب شد. حالا روش پرداخت را انتخاب کنید:", reply_markup=get_payment_method_keyboard(plan_id), parse_mode="HTML")
        finally:
            db.close()

    elif data.startswith("pay_card_"):
        payload = data.replace("pay_card_", "")
        parts = payload.split("_")
        plan_id = int(parts[0])
        renew_config_id = int(parts[1]) if len(parts) > 1 else None
        db = SessionLocal()
        try:
            plan = db.query(Plan).filter(Plan.id == plan_id).first()
            if plan:
                current = user_payment_state.get(user_id, {})
                discount_amount = int(current.get("discount_amount", 0) or 0)
                final_price = max(plan.price - discount_amount, 0)
                user_payment_state[user_id] = {
                    "plan_id": plan_id,
                    "plan_name": plan.name,
                    "price": final_price,
                    "method": "card_to_card",
                    "renew_config_id": renew_config_id,
                    "gift_code": current.get("gift_code"),
                    "server_id": current.get("server_id")
                }
                msg = f"💳 پرداخت کارت به کارت\n\nپلن: {plan.name}\nقیمت نهایی: {final_price} تومان\n\nلطفاً به شماره کارت زیر واریز کنید:\n\n🪪 شماره کارت:\n<code>{CARD_NUMBER}</code>\n\n👤 صاحب حساب: {CARD_HOLDER}\n\nپس از واریز، تصویر فیش واریزی را ارسال کنید."
                await callback.message.answer(msg, parse_mode="HTML")
            else:
                await callback.message.answer("❌ پلن یافت نشد.", parse_mode="HTML")
        finally:
            db.close()
    
    elif data.startswith("pay_wallet_"):
        payload = data.replace("pay_wallet_", "")
        parts = payload.split("_")
        plan_id = int(parts[0])
        renew_config_id = int(parts[1]) if len(parts) > 1 else None
        db = SessionLocal()
        try:
            plan = db.query(Plan).filter(Plan.id == plan_id).first()
            user = get_user(db, str(user_id))
            if plan and user:
                current = user_payment_state.get(user_id, {})
                discount_amount = int(current.get("discount_amount", 0) or 0)
                final_price = max(plan.price - discount_amount, 0)
                if user.wallet_balance >= final_price:
                    user.wallet_balance -= final_price
                    db.commit()
                    await callback.message.answer(
                        f"✅ پرداخت موفق!\n\nپلن: {plan.name}\nقیمت نهایی: {final_price} تومان",
                        parse_mode="HTML"
                    )
                else:
                    await callback.message.answer(
                        f"❌ موجودی کیف پول کافی نیست!\n\nموجودی فعلی: {user.wallet_balance} تومان\nقیمت پلن: {final_price} تومان\n\nبرای شارژ کیف پول با پشتیبانی تماس بگیرید.",
                        parse_mode="HTML"
                    )
            else:
                await callback.message.answer("❌ پلن یا کاربر یافت نشد.", parse_mode="HTML")
        finally:
            db.close()
    
    elif data.startswith("receipt_approve_"):
        if not is_admin(user_id):
            await callback.answer("❌ دسترسی ندارید.", show_alert=True)
            return
        receipt_id = int(data.split("_")[-1])
        db = SessionLocal()
        try:
            receipt = db.query(PaymentReceipt).filter(PaymentReceipt.id == receipt_id).first()
            if receipt:
                receipt.status = "approved"
                receipt.approved_at = datetime.utcnow()
                receipt.approved_by = str(user_id)
                db.commit()
                
                # Create WireGuard account
                wg_created = False
                client_ip = "N/A"
                
                try:
                    import wireguard
                    plan = db.query(Plan).filter(Plan.id == receipt.plan_id).first()
                    server = db.query(Server).filter(Server.id == receipt.server_id).first() if receipt.server_id else None
                    if not server and plan:
                        available = get_available_servers_for_plan(db, plan.id)
                        server = available[0] if available else None
                    if not server:
                        raise ValueError("سرور در دسترس برای این پلن وجود ندارد")
                    wg_result = wireguard.create_wireguard_account(**build_wg_kwargs(server, receipt.user_telegram_id, plan, receipt.plan_name, plan.duration_days if plan else None))
                    
                    if wg_result.get("success"):
                        wg_created = True
                        client_ip = wg_result.get("client_ip", "N/A")
                        
                        # Send config to user
                        try:
                            user_tg_id = int(receipt.user_telegram_id)
                            config = wg_result.get("config", "")
                            
                            # Send config as file
                            if config:
                                import tempfile
                                import os
                                tmp_path = None
                                try:
                                    with tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False, encoding="utf-8") as tmp:
                                        tmp.write(config)
                                        tmp_path = tmp.name

                                    await callback.message.bot.send_document(
                                        chat_id=user_tg_id,
                                        document=FSInputFile(tmp_path, filename="wireguard.conf"),
                                        caption="📄 فایل کانفیگ WireGuard"
                                    )
                                finally:
                                    if tmp_path and os.path.exists(tmp_path):
                                        os.remove(tmp_path)
                            
                            # Send QR code if available
                            if wg_result.get("qr_code"):
                                try:
                                    await send_qr_code(
                                        callback.message.bot,
                                        wg_result.get("qr_code"),
                                        (
                                            "📷 QR Code WireGuard\n\n"
                                            "➕ این تصویر را در نرم‌افزار WireGuard اضافه کنید\n\n"
                                            f"🏷 نام کانفیگ: <code>{wg_result.get('peer_comment', 'نامشخص')}</code>\n"
                                            f"📦 پلن انتخابی: {receipt.plan_name}"
                                        ),
                                        chat_id=user_tg_id
                                    )
                                except Exception as e:
                                    print(f"Error sending QR code to user: {e}")
                        except Exception as e:
                            print(f"Error sending to user: {e}")
                    else:
                        print(f"WireGuard creation failed: {wg_result.get('error')}")
                except Exception as e:
                    print(f"WireGuard error: {e}")
                
                # Send confirmation to admin
                if wg_created:
                    plan = db.query(Plan).filter(Plan.id == receipt.plan_id).first()
                    plan_info = f"• پلن: {receipt.plan_name}\n"
                    if plan:
                        plan_info += f"• مدت: {plan.duration_days} روز\n• حجم: {plan.traffic_gb} گیگ\n• قیمت: {plan.price:,} تومان\n"
                    await callback.message.answer(
                        f"✅ پرداخت تایید شد!\n\n{plan_info}• مبلغ: {receipt.amount:,} تومان\n• کاربر: {receipt.user_telegram_id}\n\nحساب WireGuard ایجاد شد:\n• آی پی: {client_ip}",
                        reply_markup=get_receipt_done_keyboard(),
                        parse_mode="HTML"
                    )
                else:
                    await callback.message.answer(
                        f"✅ پرداخت تایید شد!\n\n• پلن: {receipt.plan_name}\n• مبلغ: {receipt.amount} تومان\n• کاربر: {receipt.user_telegram_id}\n\n⚠️ حساب WireGuard ایجاد نشد. لطفاً دستی ایجاد کنید.",
                        reply_markup=get_receipt_done_keyboard(),
                        parse_mode="HTML"
                    )
            else:
                await callback.message.answer("❌ فیش پرداخت یافت نشد.", parse_mode="HTML")
        except Exception as e:
            await callback.message.answer(f"❌ خطا: {str(e)}", parse_mode="HTML")
        finally:
            db.close()
    
    elif data.startswith("receipt_reject_"):
        if not is_admin(user_id):
            await callback.answer("❌ دسترسی ندارید.", show_alert=True)
            return
        receipt_id = int(data.split("_")[-1])
        admin_receipt_reject_state[user_id] = {"receipt_id": receipt_id}
        await callback.message.answer("❌ لطفاً دلیل رد کردن فیش را بنویسید:", parse_mode="HTML")
    
    elif data == "back_to_main":
        db = SessionLocal()
        try:
            user = get_user(db, str(user_id))
            await callback.message.answer(WELCOME_MESSAGE, reply_markup=get_main_keyboard(user.is_admin if user else False), parse_mode="HTML")
        finally:
            db.close()
    
    elif data == "receipt_done":
        await callback.answer("این فیش قبلاً تایید شده است.", show_alert=True)
    
    elif data == "server_add_cancel":
        if user_id in admin_server_state:
            del admin_server_state[user_id]
        await callback.message.answer("❌ عملیات لغو شد.", parse_mode="HTML")
    
    await callback.answer()


@dp.message(lambda message: message.from_user.id in user_payment_state and user_payment_state.get(message.from_user.id, {}).get("step") == "discount_code")
async def handle_discount_code_input(message: Message):
    user_id = message.from_user.id
    code_text = message.text.strip().upper()
    state = user_payment_state.get(user_id, {})
    plan_id = state.get("plan_id")
    if not plan_id:
        await message.answer("❌ ابتدا پلن را انتخاب کنید.", parse_mode="HTML")
        return

    db = SessionLocal()
    try:
        plan = db.query(Plan).filter(Plan.id == plan_id).first()
        gift = db.query(GiftCode).filter(GiftCode.code == code_text, GiftCode.is_active == True).first()
        if not plan or not gift:
            await message.answer("❌ کد تخفیف نامعتبر است.", parse_mode="HTML")
            return
        if gift.expires_at and gift.expires_at < datetime.utcnow():
            await message.answer("❌ اعتبار این کد تخفیف تمام شده است.", parse_mode="HTML")
            return
        if gift.used_count >= gift.max_uses:
            await message.answer("❌ ظرفیت استفاده این کد تکمیل شده است.", parse_mode="HTML")
            return

        discount_amount = 0
        if gift.discount_percent:
            discount_amount = int((plan.price * gift.discount_percent) / 100)
        elif gift.discount_amount:
            discount_amount = gift.discount_amount

        final_price = max(plan.price - discount_amount, 0)
        state["discount_amount"] = discount_amount
        state["price"] = final_price
        state["gift_code"] = gift.code
        state.pop("step", None)
        user_payment_state[user_id] = state

        renew_config_id = state.get("renew_config_id")
        kb = get_payment_method_keyboard_for_renew(plan.id, renew_config_id) if renew_config_id else get_payment_method_keyboard(plan.id)
        await message.answer(
            f"✅ کد اعمال شد.\nقیمت اصلی: {plan.price} تومان\nمیزان تخفیف: {discount_amount} تومان\nقیمت نهایی: {final_price} تومان",
            reply_markup=kb,
            parse_mode="HTML"
        )
    finally:
        db.close()


# Admin tutorial media handler (photo/video)
@dp.message(lambda message: message.from_user.id in admin_tutorial_state and admin_tutorial_state.get(message.from_user.id, {}).get("step") == "media")
async def handle_tutorial_media(message: Message):
    user_id = message.from_user.id
    
    if user_id not in admin_tutorial_state:
        return
    
    state = admin_tutorial_state[user_id]
    if state.get("step") != "media":
        return
    
    service_type_id = state.get("service_type_id")
    
    # Check for photo
    if message.photo:
        file_id = message.photo[-1].file_id
        media_type = "photo"
    # Check for video
    elif message.video:
        file_id = message.video.file_id
        media_type = "video"
    else:
        await message.answer("❌ لطفاً عکس یا ویدیو ارسال کنید.", parse_mode="HTML")
        return
    
    db = SessionLocal()
    try:
        # Check if tutorial exists and update, or create new
        existing = db.query(ServiceTutorial).filter(
            ServiceTutorial.service_type_id == service_type_id
        ).first()
        
        if existing:
            existing.title = state.get("title", "")
            existing.description = state.get("description", "")
            existing.media_type = media_type
            existing.media_file_id = file_id
            existing.updated_at = datetime.utcnow()
        else:
            tutorial = ServiceTutorial(
                service_type_id=service_type_id,
                title=state.get("title", ""),
                description=state.get("description", ""),
                media_type=media_type,
                media_file_id=file_id,
                is_active=True
            )
            db.add(tutorial)
        
        db.commit()
        await message.answer(
            f"✅ آموزش ذخیره شد!\nرسانه: {'عکس' if media_type == 'photo' else 'ویدیو'}",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"❌ خطا: {e}", parse_mode="HTML")
    finally:
        db.close()
        del admin_tutorial_state[user_id]


# Receipt photo handler
@dp.message(lambda message: message.from_user.id in user_payment_state and user_payment_state.get(message.from_user.id, {}).get("method") == "card_to_card")
async def handle_receipt_photo(message: Message):
    user_id = message.from_user.id
    
    # Check if user is in payment state and expecting a receipt
    if user_id not in user_payment_state:
        return
    
    payment_info = user_payment_state[user_id]
    if payment_info.get("method") != "card_to_card":
        return
    
    # Check if message has a photo
    if not message.photo:
        await message.answer("❌ لطفاً تصویر فیش واریزی را ارسال کنید.", parse_mode="HTML")
        return
    
    # Get the photo file ID
    photo = message.photo[-1]  # Get the highest resolution
    file_id = photo.file_id
    
    # Save receipt to database
    db = SessionLocal()
    try:
        receipt = PaymentReceipt(
            user_telegram_id=str(user_id),
            plan_id=payment_info["plan_id"],
            plan_name=payment_info["plan_name"],
            amount=payment_info["price"],
            payment_method="card_to_card",
            server_id=payment_info.get("server_id"),
            receipt_file_id=file_id,
            status="pending"
        )
        db.add(receipt)

        gift_code = payment_info.get("gift_code")
        if gift_code:
            gift = db.query(GiftCode).filter(GiftCode.code == gift_code).first()
            if gift:
                gift.used_count = (gift.used_count or 0) + 1

        db.commit()
        
        # Clear payment state
        del user_payment_state[user_id]
        
        # Send confirmation to user
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        await message.answer(
            "✅ فیش پرداخت دریافت شد!\n\n⏰ لطفاً منتظر تایید پرداخت توسط مدیریت باشید.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="back_to_main")]
            ]),
            parse_mode="HTML"
        )
        
        # Get user info for admin notification
        user = message.from_user
        user_display_name = f"{user.first_name}"
        if user.last_name:
            user_display_name += f" {user.last_name}"
        user_username = f"@{user.username}" if user.username else "ندارد"
        
        # Forward receipt to admin
        for admin_id in ADMIN_IDS:
            try:
                # Send photo with user info in caption
                caption_text = f"💳 درخواست تایید پرداخت جدید\n\n👤 اطلاعات کاربر:\n• نام: {user_display_name}\n• آیدی: {user_id}\n• نام کاربری: {user_username}\n\n💰 اطلاعات پرداخت:\n• پلن: {payment_info['plan_name']}\n• مبلغ: {payment_info['price']} تومان\n• روش پرداخت: کارت به کارت"
                await message.bot.send_photo(
                    chat_id=admin_id,
                    photo=file_id,
                    caption=caption_text,
                    reply_markup=get_receipt_action_keyboard(receipt.id),
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Error sending to admin: {e}")
                
    except Exception as e:
        await message.answer(f"❌ خطا در ذخیره فیش: {str(e)}", parse_mode="HTML")
    finally:
        db.close()
