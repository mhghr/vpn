import json
import os
import io
from datetime import datetime

from aiogram import Dispatcher
from aiogram.types import Message, CallbackQuery, InputFile

from database import SessionLocal, engine
from models import User, Panel, Plan, PaymentReceipt, WireGuardConfig
from config import (
    CHANNEL_ID, CHANNEL_USERNAME, ADMIN_IDS,
    admin_plan_state, admin_create_account_state, user_payment_state,
    CARD_NUMBER, CARD_HOLDER,
    MIKROTIK_HOST, MIKROTIK_USER, MIKROTIK_PASS, MIKROTIK_PORT,
    WG_INTERFACE, WG_SERVER_PUBLIC_KEY, WG_SERVER_ENDPOINT, WG_SERVER_PORT,
    WG_CLIENT_NETWORK_BASE, WG_CLIENT_DNS
)

from keyboards import (
    get_main_keyboard, get_admin_keyboard, get_panels_keyboard,
    get_pending_panel_keyboard, get_plans_keyboard, get_plan_list_keyboard,
    get_plan_action_keyboard, get_plan_edit_keyboard, get_buy_keyboard,
    get_payment_method_keyboard, get_receipt_action_keyboard, get_create_account_keyboard
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
        
        # Create BytesIO
        image_io = io.BytesIO(image_data)
        image_io.name = 'qrcode.png'
        
        # Send photo based on sender type
        if chat_id:
            # Using bot.send_photo
            await sender.send_photo(chat_id=chat_id, photo=InputFile(image_io), caption=caption)
        else:
            # Using message.answer_photo
            await sender.answer_photo(photo=InputFile(image_io), caption=caption)
    except Exception as e:
        print(f"Error sending QR code: {e}")


def get_plan_field_prompt(field: str, current_value: str = None) -> str:
    prompts = {
        "name": "📝 لطفاً نام پلن را وارد کنید:",
        "days": "⏰ لطفاً مدت زمان پلن را به روز وارد کنید (عدد):",
        "traffic": "🌐 لطفاً میزان ترافیک را به گیگابایت وارد کنید (عدد):",
        "price": "💰 لطفاً قیمت پلن را به تومان وارد کنید (عدد):",
        "description": "📄 لطفاً توضیحات پلن را وارد کنید:"
    }
    msg = prompts.get(field, "لطفاً مقدار را وارد کنید:")
    if current_value:
        msg += f"\n\nمقدار فعلی: {current_value}"
    return msg


# Messages
WELCOME_MESSAGE = "🌟 به ربات فروش وی پی ان خوش آمدید!\n\n✨ با استفاده از این ربات می‌توانید:\n• بهترین سرویس‌های وی پی ان را خریداری کنید\n• لینک‌های اتصال خود را مدیریت کنید\n• وضعیت سرویس خود را بررسی کنید\n\nاز دکمه‌های زیر استفاده کنید:"
NOT_MEMBER_MESSAGE = f"❌ برای استفاده از این ربات ابتدا باید در کانال ما عضو شوید.\n\n📢 <a href=\"https://t.me/{CHANNEL_USERNAME}\">@{CHANNEL_USERNAME}</a>\n\n✅ پس از عضویت، دوباره /start را بزنید."
MY_CONFIGS_MESSAGE = "🔗 کانفیگ های من\n\nشما هنوز کانفیگ فعالی ندارید.\n\nبرای خرید سرویس جدید، روی دکمه «🛒 خرید» کلیک کنید."
WALLET_MESSAGE = "💰 شارژ کیف پول\n\nموجودی فعلی شما: 0 تومان\n\nبرای شارژ کیف پول، لطفاً با پشتیبانی تماس بگیرید."
ADMIN_MESSAGE = "⚙️ پنل مدیریت\n\nیکی از گزینه‌های زیر را انتخاب کنید:"
PANELS_MESSAGE = "🖥️ مدیریت پنل‌ها\n\nیکی از گزینه‌های زیر را انتخاب کنید:"
SEARCH_USER_MESSAGE = "🔍 جستجوی کاربر\n\nلطفاً شناسه تلگرام کاربر را وارد کنید:"
PLANS_MESSAGE = "📦 مدیریت پلن‌ها\n\nیکی از گزینه‌های زیر را انتخاب کنید:"


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
            db_user.is_member = True
            db.commit()
            await message.answer(WELCOME_MESSAGE, reply_markup=get_main_keyboard(db_user.is_admin), parse_mode="HTML")
        else:
            db_user = get_user(db, str(user_id))
            if db_user:
                db_user.is_member = False
                db.commit()
            await message.answer(NOT_MEMBER_MESSAGE, parse_mode="HTML")
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


@dp.message(lambda message: is_admin(message.from_user.id))
async def handle_admin_input(message: Message):
    user_id = message.from_user.id
    text = message.text.strip()
    
    # Handle custom account creation flow
    if user_id in admin_create_account_state:
        state = admin_create_account_state[user_id]
        step = state.get("step")
        
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
                        user_telegram_id=str(user_id)
                    )
                    
                    if wg_result.get("success"):
                        client_ip = wg_result.get("client_ip", "N/A")
                        config = wg_result.get("config", "")
                        
                        # Send to admin
                        await message.answer(
                            f"✅ اکانت وایرگارد دلخواه ایجاد شد!\n\n📋 اطلاعات اکانت:\n• مدت: {days} روز\n• حجم: {traffic} گیگ\n• آی پی: {client_ip}\n\nکانفیگ:\n<code>{config}</code>",
                            parse_mode="HTML"
                        )
                        
                        # Send QR if available
                        if wg_result.get("qr_code"):
                            await send_qr_code(
                                message,
                                wg_result.get("qr_code"),
                                f"QR Code - {days}روز / {traffic}گیگ"
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
        field = state.get("field")
        
        if field:
            if field in ["days", "traffic", "price"]:
                text = normalize_numbers(text)
                try:
                    int(text)
                except ValueError:
                    await message.answer("❌ لطفاً یک عدد صحیح وارد کنید.", parse_mode="HTML")
                    return
            state["data"][field] = text
            plan_id = state.get("plan_id", "new")
            action = "ویرایش" if state.get("action") == "edit" else "ایجاد"
            if plan_id == "new":
                await message.answer(f"➕ {action} پلن جدید\n\nاطلاعات وارد شده:\n• نام: {state['data'].get('name', '➖')}\n• مدت: {state['data'].get('days', '➖')} روز\n• ترافیک: {state['data'].get('traffic', '➖')} گیگ\n• قیمت: {state['data'].get('price', '➖')} تومان\n• توضیحات: {state['data'].get('description', '➖')}", reply_markup=get_plan_edit_keyboard(), parse_mode="HTML")
            else:
                await message.answer(f"✏️ {action} پلن\n\nاطلاعات وارد شده:\n• نام: {state['data'].get('name', '➖')}\n• مدت: {state['data'].get('days', '➖')} روز\n• ترافیک: {state['data'].get('traffic', '➖')} گیگ\n• قیمت: {state['data'].get('price', '➖')} تومان\n• توضیحات: {state['data'].get('description', '➖')}", reply_markup=get_plan_edit_keyboard(int(plan_id)), parse_mode="HTML")
            return
        
        # Parse input format: name-volume-days-price (with optional spaces around hyphens)
        parts = [p.strip() for p in text.split("-") if p.strip()]
        if len(parts) >= 4:
            try:
                plan_name = "-".join(parts[:-3]).strip()  # Allow hyphens in plan name
                # Convert Persian/Arabic numbers to English
                traffic = int(normalize_numbers(parts[-3].strip()))
                days = int(normalize_numbers(parts[-2].strip()))
                price = int(normalize_numbers(parts[-1].strip()))
                
                db = SessionLocal()
                try:
                    plan = Plan(name=plan_name, duration_days=days, traffic_gb=traffic, price=price, is_active=True)
                    db.add(plan)
                    db.commit()
                    del admin_plan_state[user_id]
                    await message.answer(f"✅ پلن «{plan_name}» با موفقیت ایجاد شد!\n\n• حجم: {traffic} گیگ\n• مدت: {days} روز\n• قیمت: {price} تومان", parse_mode="HTML")
                    # Show the plans list
                    all_plans = db.query(Plan).all()
                    await message.answer(PLANS_MESSAGE, reply_markup=get_plans_keyboard(all_plans), parse_mode="HTML")
                finally:
                    db.close()
            except Exception as e:
                await message.answer(f"❌ خطا: {str(e)}", parse_mode="HTML")
        else:
            await message.answer("❌ فرمت نادرست!\n\nلطفاً به این فرمت وارد کنید:\nنام-حجم-روز-قیمت\n\nمثال: وی پی ان-50-30-300000", parse_mode="HTML")
        return
    
    db = SessionLocal()
    try:
        user = get_user(db, text) or db.query(User).filter(User.username == text).first()
        if user:
            msg = f"👤 اطلاعات کاربر:\n\nشناسه: {user.telegram_id}\nنام: {user.first_name}\nنام کاربری: @{user.username}\nموجودی: {user.wallet_balance} تومان\nتاریخ عضویت: {user.joined_at}\nوضعیت: {'✅ فعال' if user.is_member else '❌ غیرفعال'}\nادمین: {'✅ بله' if user.is_admin else '❌ خیر'}"
            await message.answer(msg, parse_mode="HTML")
        else:
            await message.answer("❌ کاربر یافت نشد.", parse_mode="HTML")
    finally:
        db.close()


@dp.callback_query()
async def callback_handler(callback: CallbackQuery, bot):
    data = callback.data
    user_id = callback.from_user.id
    
    if data.startswith(("admin_", "panel_", "plan_")) or data == "admin":
        if not is_admin(user_id):
            await callback.answer("❌ شما دسترسی مدیریت ندارید.", show_alert=True)
            return
    
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
    
    elif data == "software":
        await callback.message.answer("📱 نرم افزارهای مورد نیاز\n\nبرای اتصال به وی پی ان می‌توانید از نرم افزارهای زیر استفاده کنید:\n\n• V2RayNG (اندروید)\n• V2Box (آیفون)\n• V2Ray (ویندوز/مک/لینوکس)\n\nدر حال آماده‌سازی لینک دانلود...", parse_mode="HTML")
    
    elif data == "configs":
        db = SessionLocal()
        try:
            user = get_user(db, str(user_id))
            if user and user.is_admin:
                await callback.message.answer(MY_CONFIGS_MESSAGE + "\n\n(نمایش کانفیگ‌های ادمین)", parse_mode="HTML")
            else:
                await callback.message.answer(MY_CONFIGS_MESSAGE, parse_mode="HTML")
        finally:
            db.close()
    
    elif data == "wallet":
        db = SessionLocal()
        try:
            user = get_user(db, str(user_id))
            if user:
                await callback.message.answer(f"💰 شارژ کیف پول\n\nموجودی فعلی شما: {user.wallet_balance} تومان\n\nبرای شارژ کیف پول، لطفاً با پشتیبانی تماس بگیرید.", parse_mode="HTML")
            else:
                await callback.message.answer(WALLET_MESSAGE, parse_mode="HTML")
        finally:
            db.close()
    
    # === ADMIN CALLBACKS ===
    elif data == "admin":
        pending_panel = load_pending_panel()
        await callback.message.answer(ADMIN_MESSAGE, reply_markup=get_admin_keyboard(pending_panel), parse_mode="HTML")
    
    elif data == "admin_panels":
        pending_panel = load_pending_panel()
        await callback.message.answer(PANELS_MESSAGE, reply_markup=get_panels_keyboard(pending_panel), parse_mode="HTML")
    
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
        await callback.message.answer(SEARCH_USER_MESSAGE, parse_mode="HTML")
    
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
            if plan:
                # Create WireGuard account
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
                        user_telegram_id=str(user_id)
                    )
                    
                    if wg_result.get("success"):
                        client_ip = wg_result.get("client_ip", "N/A")
                        config = wg_result.get("config", "")
                        
                        # Send to admin
                        await callback.message.answer(
                            f"✅ اکانت وایرگارد ایجاد شد!\n\n📋 اطلاعات اکانت:\n• پلن: {plan.name}\n• مدت: {plan.duration_days} روز\n• حجم: {plan.traffic_gb} گیگ\n• آی پی: {client_ip}\n\nکانفیگ:\n<code>{config}</code>",
                            parse_mode="HTML"
                        )
                        
                        # Send QR if available
                        if wg_result.get("qr_code"):
                            await send_qr_code(
                                callback.message,
                                wg_result.get("qr_code"),
                                f"QR Code - {plan.name}"
                            )
                    else:
                        await callback.message.answer(
                            f"❌ خطا در ایجاد اکانت: {wg_result.get('error', 'خطای نامشخص')}",
                            parse_mode="HTML"
                        )
                except Exception as e:
                    await callback.message.answer(f"❌ خطا در ایجاد اکانت: {str(e)}", parse_mode="HTML")
            else:
                await callback.message.answer("❌ پلن یافت نشد یا غیرفعال است.", parse_mode="HTML")
        finally:
            db.close()
    
    elif data == "create_acc_custom":
        # Start custom plan flow - ask for days
        admin_create_account_state[user_id] = {"step": "days"}
        await callback.message.answer(
            "📝 ساخت پلن دلخواه\n\nلطفاً تعداد روز را وارد کنید:\n(عدد صحیح)",
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
    
    elif data == "plan_create":
        admin_plan_state[user_id] = {"action": "create", "plan_id": "new", "data": {}}
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        await callback.message.answer(
            "➕ ایجاد پلن جدید\n\n"
            "📋 لطفاً اطلاعات پلن را به این فرمت وارد کنید:\n\n"
            "نام-حجم(گیگ)-روز-قیمت(تومان)\n\n"
            "مثال:\n"
            "وی پی ان پریمیوم-50-30-300000",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 انصراف", callback_data="admin_plans")]
            ]),
            parse_mode="HTML"
        )
    
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
                admin_plan_state[user_id] = {"action": "edit", "plan_id": plan_id, "data": {"name": plan.name, "days": str(plan.duration_days), "traffic": str(plan.traffic_gb), "price": str(plan.price), "description": plan.description or ""}}
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
        admin_plan_state[user_id] = {"action": "create" if plan_id == "new" else "edit", "plan_id": plan_id, "field": "name"}
        await callback.message.answer(get_plan_field_prompt("name"), parse_mode="HTML")
    
    elif data.startswith("plan_set_days_"):
        plan_id = data.split("_")[-1]
        current = admin_plan_state.get(user_id, {}).get("data", {}).get("days", "")
        admin_plan_state[user_id] = {"action": "create" if plan_id == "new" else "edit", "plan_id": plan_id, "field": "days"}
        await callback.message.answer(get_plan_field_prompt("days", current), parse_mode="HTML")
    
    elif data.startswith("plan_set_traffic_"):
        plan_id = data.split("_")[-1]
        current = admin_plan_state.get(user_id, {}).get("data", {}).get("traffic", "")
        admin_plan_state[user_id] = {"action": "create" if plan_id == "new" else "edit", "plan_id": plan_id, "field": "traffic"}
        await callback.message.answer(get_plan_field_prompt("traffic", current), parse_mode="HTML")
    
    elif data.startswith("plan_set_price_"):
        plan_id = data.split("_")[-1]
        current = admin_plan_state.get(user_id, {}).get("data", {}).get("price", "")
        admin_plan_state[user_id] = {"action": "create" if plan_id == "new" else "edit", "plan_id": plan_id, "field": "price"}
        await callback.message.answer(get_plan_field_prompt("price", current), parse_mode="HTML")
    
    elif data.startswith("plan_set_desc_"):
        plan_id = data.split("_")[-1]
        current = admin_plan_state.get(user_id, {}).get("data", {}).get("description", "")
        admin_plan_state[user_id] = {"action": "create" if plan_id == "new" else "edit", "plan_id": plan_id, "field": "description"}
        await callback.message.answer(get_plan_field_prompt("description", current), parse_mode="HTML")
    
    elif data == "plan_save_new":
        state = admin_plan_state.get(user_id, {})
        plan_data = state.get("data", {})
        if not all([plan_data.get("name"), plan_data.get("days"), plan_data.get("traffic"), plan_data.get("price")]):
            await callback.message.answer("❌ لطفاً تمام فیلدهای الزامی را تکمیل کنید.", parse_mode="HTML")
            return
        # Convert Persian/Arabic numbers to English
        days = normalize_numbers(plan_data.get("days", "0"))
        traffic = normalize_numbers(plan_data.get("traffic", "0"))
        price = normalize_numbers(plan_data.get("price", "0"))
        db = SessionLocal()
        try:
            plan = Plan(name=plan_data["name"], duration_days=int(days), traffic_gb=int(traffic),
                       price=int(price), description=plan_data.get("description", ""), is_active=True)
            db.add(plan)
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
        if not all([plan_data.get("name"), plan_data.get("days"), plan_data.get("traffic"), plan_data.get("price")]):
            await callback.message.answer("❌ لطفاً تمام فیلدهای الزامی را تکمیل کنید.", parse_mode="HTML")
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
            if plan:
                user_payment_state[user_id] = {"plan_id": plan_id, "plan_name": plan.name, "price": plan.price}
                msg = f"💳 پرداخت پلن \"{plan.name}\"\n\n• حجم: {plan.traffic_gb} گیگ\n• مدت: {plan.duration_days} روز\n• قیمت: {plan.price} تومان\n\nروش پرداخت را انتخاب کنید:"
                await callback.message.answer(msg, reply_markup=get_payment_method_keyboard(plan_id), parse_mode="HTML")
            else:
                await callback.message.answer("❌ پلن یافت نشد یا غیرفعال است.", parse_mode="HTML")
        finally:
            db.close()
    
    elif data.startswith("pay_card_"):
        plan_id = int(data.split("_")[-1])
        db = SessionLocal()
        try:
            plan = db.query(Plan).filter(Plan.id == plan_id).first()
            if plan:
                user_payment_state[user_id] = {"plan_id": plan_id, "plan_name": plan.name, "price": plan.price, "method": "card_to_card"}
                msg = f"💳 پرداخت کارت به کارت\n\nپلن: {plan.name}\nقیمت: {plan.price} تومان\n\nلطفاً به شماره کارت زیر واریز کنید:\n\n🪪 شماره کارت:\n<code>{CARD_NUMBER}</code>\n\n👤 صاحب حساب: {CARD_HOLDER}\n\nپس از واریز، تصویر فیش واریزی را ارسال کنید."
                await callback.message.answer(msg, parse_mode="HTML")
            else:
                await callback.message.answer("❌ پلن یافت نشد.", parse_mode="HTML")
        finally:
            db.close()
    
    elif data.startswith("pay_wallet_"):
        plan_id = int(data.split("_")[-1])
        db = SessionLocal()
        try:
            plan = db.query(Plan).filter(Plan.id == plan_id).first()
            user = get_user(db, str(user_id))
            if plan and user:
                if user.wallet_balance >= plan.price:
                    user.wallet_balance -= plan.price
                    db.commit()
                    await callback.message.answer(
                        f"✅ پرداخت موفق!\n\nپلن: {plan.name}\nقیمت: {plan.price} تومان\n\nحساب کاربری شما ایجاد شد!\n\n👤 نام کاربری: [تخصیص داده نشد]\n🔑 رمز عبور: [تخصیص داده نشد]",
                        parse_mode="HTML"
                    )
                else:
                    await callback.message.answer(
                        f"❌ موجودی کیف پول کافی نیست!\n\nموجودی فعلی: {user.wallet_balance} تومان\nقیمت پلن: {plan.price} تومان\n\nبرای شارژ کیف پول با پشتیبانی تماس بگیرید.",
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
                        user_telegram_id=receipt.user_telegram_id,
                        plan_id=receipt.plan_id,
                        plan_name=receipt.plan_name
                    )
                    
                    if wg_result.get("success"):
                        wg_created = True
                        client_ip = wg_result.get("client_ip", "N/A")
                        
                        # Send config to user
                        try:
                            user_tg_id = int(receipt.user_telegram_id)
                            config = wg_result.get("config", "")
                            
                            await callback.message.bot.send_message(
                                chat_id=user_tg_id,
                                text=f"✅ پرداخت شما تایید شد!\n\nحساب WireGuard شما ایجاد شد:\n\n• آی پی: {client_ip}\n\nکانفیگ:",
                                parse_mode="HTML"
                            )
                            
                            # Send config text
                            if config:
                                await callback.message.bot.send_message(
                                    chat_id=user_tg_id,
                                    text=f"<code>{config}</code>",
                                    parse_mode="HTML"
                                )
                            
                            # Send QR code if available
                            if wg_result.get("qr_code"):
                                try:
                                    await send_qr_code(
                                        callback.message.bot,
                                        wg_result.get("qr_code"),
                                        f"QR Code - {receipt.plan_name}",
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
                    await callback.message.answer(
                        f"✅ پرداخت تایید شد!\n\n• پلن: {receipt.plan_name}\n• مبلغ: {receipt.amount} تومان\n• کاربر: {receipt.user_telegram_id}\n\nحساب WireGuard ایجاد شد:\n• آی پی: {client_ip}",
                        parse_mode="HTML"
                    )
                else:
                    await callback.message.answer(
                        f"✅ پرداخت تایید شد!\n\n• پلن: {receipt.plan_name}\n• مبلغ: {receipt.amount} تومان\n• کاربر: {receipt.user_telegram_id}\n\n⚠️ حساب WireGuard ایجاد نشد. لطفاً دستی ایجاد کنید.",
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
        db = SessionLocal()
        try:
            receipt = db.query(PaymentReceipt).filter(PaymentReceipt.id == receipt_id).first()
            if receipt:
                receipt.status = "rejected"
                db.commit()
                await callback.message.answer(
                    f"❌ پرداخت رد شد!\n\n• پلن: {receipt.plan_name}\n• مبلغ: {receipt.amount} تومان\n• کاربر: {receipt.user_telegram_id}",
                    parse_mode="HTML"
                )
            else:
                await callback.message.answer("❌ فیش پرداخت یافت نشد.", parse_mode="HTML")
        except Exception as e:
            await callback.message.answer(f"❌ خطا: {str(e)}", parse_mode="HTML")
        finally:
            db.close()
    
    elif data == "back_to_main":
        db = SessionLocal()
        try:
            user = get_user(db, str(user_id))
            await callback.message.answer(WELCOME_MESSAGE, reply_markup=get_main_keyboard(user.is_admin if user else False), parse_mode="HTML")
        finally:
            db.close()
    
    await callback.answer()


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
            receipt_file_id=file_id,
            status="pending"
        )
        db.add(receipt)
        db.commit()
        
        # Clear payment state
        del user_payment_state[user_id]
        
        # Send confirmation to user
        await message.answer(
            f"✅ فیش پرداخت دریافت شد!\n\n📋 اطلاعات پرداخت:\n• پلن: {payment_info['plan_name']}\n• مبلغ: {payment_info['price']} تومان\n\n⏰ لطفاً منتظر تایید پرداخت توسط مدیریت باشید.\n\nپس از تایید، حساب کاربری برای شما ارسال می‌شود.",
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
