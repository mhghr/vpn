# Bot messages - all texts used in the bot

# Main messages
WELCOME_MESSAGE = """سلااام به ربات میگ میگ خوش اومدی  🫡🌸

ما اینجاییم تا شما را بدون هیچ محدویتی به شبکه جهانی متصل کنیم ❤️

✅ کیفیت در ساخت انواع کانکشن‌ها
📡 برقراری امنیت در ارتباط شما
☎️ پشتیبانی تا روز آخر

🚪 /start"""

NOT_MEMBER_MESSAGE = """⛔ اول باید عضو کانال ما بشی

📢 <a href="https://t.me/{channel_username}">@{channel_username}</a>

✅ بعد از عضویت، دکمه /start رو بزن"""

MY_CONFIGS_MESSAGE = """🔐 کانفیگ‌های من

شما هنوز کانفیگ فعالی ندارید.

برای خرید سرویس جدید، روی دکمه «🛒 خرید سرویس» کلیک کنید."""

WALLET_MESSAGE = """💳 کیف پول

موجودی فعلی شما: {balance} تومان

برای شارژ کیف پول، لطفاً با پشتیبانی تماس بگیرید."""

ADMIN_MESSAGE = """⚙️ پنل مدیریت

یکی از گزینه‌های زیر را انتخاب کنید:"""

PANELS_MESSAGE = """🖥️ مدیریت پنل‌ها

یکی از گزینه‌های زیر را انتخاب کنید:"""

SEARCH_USER_MESSAGE = """🔎 جستجوی کاربر

لطفاً شناسه تلگرام کاربر را وارد کنید:"""

PLANS_MESSAGE = """📦 مدیریت پلن‌ها

یکی از گزینه‌های زیر را انتخاب کنید:"""

TEST_ACCOUNT_PLAN_NAME = "اکانت تست"

# Buy messages
BUY_PLANS_MESSAGE = """🛒 خرید سرویس وی‌پی‌ان

یکی از پلن‌های زیر را انتخاب کنید:
"""

NO_ACTIVE_PLANS_MESSAGE = """❌ در حال حاضر پلن فعالی برای خرید وجود ندارد."""

# Payment messages
PAYMENT_METHOD_MESSAGE = """💳 پرداخت پلن «{plan_name}»

• 🌐 حجم: {traffic_gb} گیگ
• ⏰ مدت: {duration_days} روز
• 💰 قیمت: {price} تومان

روش پرداخت را انتخاب کنید:"""

PAYMENT_CARD_MESSAGE = """💳 پرداخت کارت به کارت

پلن: {plan_name}
💰 قیمت: {price} تومان

لطفاً به شماره کارت زیر واریز کنید:

🪪 شماره کارت:
<code>{card_number}</code>

👤 صاحب حساب: {card_holder}

📸 پس از واریز، تصویر فیش واریزی را ارسال کنید."""

PAYMENT_SUCCESS_MESSAGE = """✅ پرداخت موفق!

🛒 پلن: {plan_name}
💰 قیمت: {price} تومان

حساب کاربری شما ایجاد شد!"""

INSUFFICIENT_BALANCE_MESSAGE = """❌ موجودی کیف پول کافی نیست!

💰 موجودی فعلی: {balance} تومان
💵 قیمت پلن: {price} تومان

برای شارژ کیف پول با پشتیبانی تماس بگیرید."""

WAIT_APPROVAL_MESSAGE = """✅ فیش پرداخت دریافت شد!

📋 اطلاعات پرداخت:
• 🛒 پلن: {plan_name}
• 💰 مبلغ: {price} تومان
• 📅 تاریخ: {date}

⏰ لطفاً منتظر تایید پرداخت توسط مدیریت باشید.

✅ پس از تایید، حساب کاربری برای شما ارسال می‌شود."""

# Receipt admin messages
RECEIPT_APPROVED_MESSAGE = """✅ پرداخت تایید شد!

📋 اطلاعات پرداخت:
• 🛒 پلن: {plan_name}
• 💰 مبلغ: {price} تومان
• 👤 کاربر: {user_id}

حساب کاربری به زودی ایجاد و ارسال می‌شود."""

RECEIPT_REJECTED_MESSAGE = """❌ پرداخت رد شد!

📋 اطلاعات پرداخت:
• 🛒 پلن: {plan_name}
• 💰 مبلغ: {price} تومان
• 👤 کاربر: {user_id}"""

RECEIPT_ADMIN_MESSAGE = """💳 درخواست تایید پرداخت جدید

📋 اطلاعات پرداخت:
• 🛒 پلن: {plan_name}
• 💰 مبلغ: {price} تومان
• 👤 کاربر: {user_id}
• 📅 تاریخ: {date}
• 💳 روش پرداخت: کارت به کارت

تصویر فیش پرداخت در پیام قبلی."""

# Plan messages
PLAN_DETAIL_MESSAGE = """📦 اطلاعات پلن

• 📝 نام: {name}
• ⏰ مدت: {duration_days} روز
• 🌐 ترافیک: {traffic_gb} گیگابایت
• 💰 قیمت: {price} تومان
• ✅ وضعیت: {status}
• 📄 توضیحات: {description}"""

PLAN_CREATED_MESSAGE = """✅ پلن «{name}» با موفقیت ایجاد شد!

• 🌐 حجم: {traffic_gb} گیگ
• ⏰ مدت: {duration_days} روز
• 💰 قیمت: {price} تومان"""

PLAN_EDIT_MESSAGE = """✏️ ویرایش پلن: {name}

می‌توانید هر فیلدی را که می‌خواهید تغییر دهید:"""

PLAN_SAVED_MESSAGE = """✅ پلن «{name}» با موفقیت ویرایش شد!"""

PLAN_DELETED_MESSAGE = """✅ پلن «{name}» با موفقیت حذف شد."""

PLAN_TOGGLE_MESSAGE = """✅ پلن «{name}» {status} شد."""

PLAN_NOT_FOUND_MESSAGE = """❌ پلن یافت نشد."""

PLAN_NO_ACTIVE_MESSAGE = """❌ پلن یافت نشد یا غیرفعال است."""

# Software message
SOFTWARE_MESSAGE = """📱 نرم‌افزارهای مورد نیاز

برای اتصال به وی‌پی‌ان می‌توانید از نرم‌افزارهای زیر استفاده کنید:

• 📱 V2RayNG (اندروید)
• 🍎 V2Box (آیفون)
• 💻 V2Ray (ویندوز/مک/لینوکس)

در حال آماده‌سازی لینک دانلود..."""

# User info message
USER_INFO_MESSAGE = """👤 اطلاعات کاربر:

• 🆔 شناسه: {telegram_id}
• 👤 نام: {first_name}
• 📛 نام کاربری: @{username}
• 💰 موجودی: {wallet_balance} تومان
• 📅 تاریخ عضویت: {joined_at}
• ✅ وضعیت: {member_status}
• ⚙️ ادمین: {admin_status}"""

# Panel messages
PANEL_DETAIL_MESSAGE = """📋 {name}

📍 لوکیشن: {location}
🌐 آی‌پی: {ip_address}:{port}
📁 مسیر: {path}
👤 نام کاربری: {api_username}"""

PANEL_PENDING_MESSAGE = """🔔 درخواست ثبت پنل جدید

📍 اطلاعات پنل:
• 🏷️ نام: {name}
• 🌐 آی‌پی: {ip}
• 📍 لوکیشن: {location}
• 🔌 پورت: {port}
• 📁 مسیر: {path}

📊 اطلاعات سیستم:
• 🖥️ هاست‌نیم: {hostname}
• 💿 سیستم عامل: {os}"""

PANEL_FULL_DETAIL_MESSAGE = """📋 جزئیات کامل پنل

• 🏷️ نام: {name}
• 🌐 آی‌پی: {ip}
• 🏠 آی‌پی محلی: {local_ip}
• 📍 لوکیشن: {location}
• 🔌 پورت: {port}
• 📁 مسیر: {path}
• 👤 نام کاربری: {username}
• 🔑 رمز عبور: {password}
• 📦 نسخه X-UI: {xui_version}
• 🕐 زمان: {timestamp}"""

PANEL_APPROVED_MESSAGE = """✅ پنل با موفقیت تایید و ذخیره شد!"""

PANEL_REJECTED_MESSAGE = """❌ درخواست پنل رد شد."""

PANEL_NOT_FOUND_MESSAGE = """❌ پنل تایید شده‌ای یافت نشد."""

# Create plan messages
PLAN_CREATE_PROMPT = """➕ ایجاد پلن جدید

📋 لطفاً اطلاعات پلن را به این فرمت وارد کنید:

نام-حجم(گیگ)-روز-قیمت(تومان)

مثال:
وی‌پی‌ان پریمیوم-50-30-300000"""

PLAN_CREATE_PROMPT_NEW = """➕ ایجاد پلن جدید

📋 لطفاً اطلاعات پلن را به این فرمت وارد کنید:

نام-حجم(گیگ)-روز-قیمت(تومان)

مثال:
وی‌پی‌ان پریمیوم-50-30-300000"""

# Plan field prompts
PLAN_FIELD_PROMPTS = {
    "name": "📝 لطفاً نام پلن را وارد کنید:",
    "days": "⏰ لطفاً مدت زمان پلن را به روز وارد کنید (عدد):",
    "traffic": "🌐 لطفاً میزان ترافیک را به گیگابایت وارد کنید (عدد):",
    "price": "💰 لطفاً قیمت پلن را به تومان وارد کنید (عدد):",
    "description": "📄 لطفاً توضیحات پلن را وارد کنید:"
}

# Error messages
ERROR_MESSAGE = "❌ خطایی رخ داد. لطفاً دوباره تلاش کنید."
INVALID_FORMAT_MESSAGE = """❌ فرمت نادرست!

لطفاً به این فرمت وارد کنید:
نام-حجم-روز-قیمت

مثال: وی‌پی‌ان-50-30-300000"""

INVALID_NUMBER_MESSAGE = "❌ لطفاً یک عدد صحیح وارد کنید."
INCOMPLETE_FIELDS_MESSAGE = "❌ لطفاً تمام فیلدهای الزامی را تکمیل کنید."
SAVE_ERROR_MESSAGE = "❌ خطا در ذخیره: {error}"
DELETE_ERROR_MESSAGE = "❌ خطا در حذف: {error}"

# Access denied messages
NOT_ADMIN_MESSAGE = "❌ شما دسترسی ادمین ندارید."
NO_ADMIN_ACCESS_MESSAGE = "❌ شما دسترسی مدیریت ندارید."

# No panel pending message
NO_PANEL_REQUEST_MESSAGE = """❌ درخواست پنل جدیدی وجود ندارد.

ابتدا agent را روی سرور اجرا کنید."""

# Plan list message
PLAN_LIST_MESSAGE = "📋 لیست پلن‌ها:"

PLAN_LIST_EMPTY_MESSAGE = """❌ پلنی یافت نشد.

برای ایجاد پلن جدید، دکمه «➕ پلن جدید» را بزنید."""

# Wallet info message
WALLET_INFO_MESSAGE = """💳 کیف پول

موجودی فعلی شما: {balance} تومان

برای شارژ کیف پول، لطفاً با پشتیبانی تماس بگیرید."""

# Receipt messages
RECEIPT_SAVED_MESSAGE = "❌ خطا در ذخیره فیش: {error}"
RECEIPT_NOT_FOUND_MESSAGE = "❌ فیش پرداخت یافت نشد."

# Config detail message
CONFIG_DETAIL_MESSAGE = """📋 جزئیات کانفیگ

• 🛒 پلن: {plan_name}
• 🌐 آی‌پی: {client_ip}
• 📅 تاریخ خرید: {created_at}
• ⏰ تاریخ انقضا: {expires_at}
• 📊 حجم مصرفی: {consumed}
• ⬇️ حجم دریافتی (RX): {rx}
• ⬆️ حجم ارسالی (TX): {tx}
• 💾 حجم باقی‌مانده: {remaining}"""

# WireGuard account created message
WG_ACCOUNT_CREATED_MESSAGE = """✅ اکانت وایرگارد ایجاد شد!

📋 اطلاعات اکانت:
• 🛒 پلن: {plan_name}
• ⏰ مدت: {duration_days} روز
• 🌐 حجم: {traffic_gb} گیگ
• 🌐 آی‌پی: {client_ip}

📄 کانفیگ:
<code>{config}</code>"""

# Config view messages
CONFIG_LIST_MESSAGE = """🔐 کانفیگ‌های من

برای مشاهده جزئیات، کانفیگ موردنظر را انتخاب کنید:"""

NO_CONFIG_MESSAGE = """🔐 کانفیگ‌های من

شما هنوز کانفیگ فعالی ندارید.

برای خرید سرویس جدید، روی دکمه «🛒 خرید سرویس» کلیک کنید."""
