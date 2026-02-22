from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_keyboard(is_admin_user: bool = False):
    buttons = [
        [InlineKeyboardButton(text="🔗 کانفیگ‌های من", callback_data="configs"), InlineKeyboardButton(text="🛒 خرید جدید", callback_data="buy")],
        [InlineKeyboardButton(text="📚 آموزش اتصال", callback_data="user_tutorials"), InlineKeyboardButton(text="📱 نرم‌افزارها", callback_data="software")],
        [InlineKeyboardButton(text="💳 شارژ کیف پول", callback_data="wallet"), InlineKeyboardButton(text="🧪 اکانت تست", callback_data="test_account_create")],
        [InlineKeyboardButton(text="👤 حساب کاربری", callback_data="profile")],
    ]
    if is_admin_user:
        buttons.append([InlineKeyboardButton(text="⚙️ مدیریت", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_keyboard(pending_panel=None):
    buttons = [
        [InlineKeyboardButton(text="🖥️ پنل‌ها", callback_data="admin_panels"), InlineKeyboardButton(text="🔍 جستجو", callback_data="admin_search")],
        [InlineKeyboardButton(text="📦 پلن ها", callback_data="admin_plans"), InlineKeyboardButton(text="💳 فیش‌های پرداخت", callback_data="admin_receipts")],
        [InlineKeyboardButton(text="🎁 کد تخفیف", callback_data="admin_discount_create"), InlineKeyboardButton(text="🧩 انواع سرویس", callback_data="admin_service_types")],
        [InlineKeyboardButton(text="🖧 مدیریت سرورها", callback_data="admin_servers"), InlineKeyboardButton(text="🔗 ساخت اکانت", callback_data="admin_create_account")],
        [InlineKeyboardButton(text="🤝 نمایندگی‌ها", callback_data="admin_representatives"), InlineKeyboardButton(text="📚 آموزش", callback_data="admin_tutorials")],
        [InlineKeyboardButton(text="💳 شماره کارت", callback_data="admin_card_settings")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")],
    ]
    if pending_panel:
        buttons.insert(0, [InlineKeyboardButton(text=f"🔔 درخواست پنل جدید ({pending_panel.get('name', 'Unknown')})", callback_data="admin_pending_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_panels_keyboard(pending_panel=None):
    buttons = [[InlineKeyboardButton(text="📋 لیست پنل‌ها", callback_data="panel_list"), InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin")]]
    if pending_panel:
        buttons.insert(0, [InlineKeyboardButton(text="🔔 درخواست پنل جدید", callback_data="admin_pending_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_pending_panel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ تایید", callback_data="panel_approve"), InlineKeyboardButton(text="❌ رد", callback_data="panel_reject")],
        [InlineKeyboardButton(text="ℹ️ جزئیات", callback_data="panel_details"), InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_panels")]
    ])


def get_plans_keyboard(plans: list = None):
    buttons = []
    if plans:
        for plan in plans:
            if plan.name == "اکانت تست":
                continue
            status_emoji = "🟢" if plan.is_active else "🔴"
            buttons.append([InlineKeyboardButton(text=f"{status_emoji} {plan.name}", callback_data=f"plan_view_{plan.id}")])
    else:
        buttons.append([InlineKeyboardButton(text="❌ پلنی یافت نشد", callback_data="admin_plans")])

    buttons.append([InlineKeyboardButton(text="➕ افزودن پلن جدید", callback_data="plan_create")])
    buttons.append([InlineKeyboardButton(text="🧪 اکانت تست", callback_data="plan_test_account")])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_plan_list_keyboard(plans: list):
    buttons = []
    for plan in plans:
        if plan.name == "اکانت تست":
            continue
        status_emoji = "🟢" if plan.is_active else "🔴"
        buttons.append([InlineKeyboardButton(text=f"{status_emoji} {plan.name}", callback_data=f"plan_view_{plan.id}")])
    buttons.append([InlineKeyboardButton(text="➕ پلن جدید", callback_data="plan_create")])
    buttons.append([InlineKeyboardButton(text="🧪 اکانت تست", callback_data="plan_test_account")])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_plans")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)



def get_test_account_keyboard(days_text: str = "-", traffic_text: str = "-", is_active: bool = True, has_plan: bool = False):
    status_text = "✅ فعال" if is_active else "❌ غیرفعال"
    create_or_edit = "➕ ایجاد اکانت تست" if not has_plan else "🆕 ایجاد مجدد اکانت تست"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🧪 نام پلن: اکانت تست", callback_data="test_account_ro")],
        [InlineKeyboardButton(text=f"⏰ مدت: {days_text} روز", callback_data="plan_test_set_days")],
        [InlineKeyboardButton(text=f"🌐 ترافیک: {traffic_text} گیگ", callback_data="plan_test_set_traffic")],
        [InlineKeyboardButton(text=f"💰 قیمت: 0 تومان", callback_data="test_account_ro")],
        [InlineKeyboardButton(text=f"⚙️ وضعیت: {status_text}", callback_data="plan_test_toggle")],
        [InlineKeyboardButton(text=create_or_edit, callback_data="plan_test_account_edit")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_plans")]
    ])


def get_plan_action_keyboard(plan_id: int, plan_name: str, days_text: str, traffic_text: str, price_text: str, description_text: str, is_active: bool = True, service_text: str = "-", server_text: str = "بدون سرور", has_server_mapping: bool = True):
    if not has_server_mapping:
        status_text = "🟠 غیرفعال (بدون سرور)"
    else:
        status_text = "✅ فعال" if is_active else "❌ غیرفعال"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📝 نام پلن: {plan_name}", callback_data=f"plan_set_name_{plan_id}")],
        [InlineKeyboardButton(text=f"⏰ مدت زمان: {days_text} روز", callback_data=f"plan_set_days_{plan_id}")],
        [InlineKeyboardButton(text=f"🌐 حجم ترافیک: {traffic_text} گیگ", callback_data=f"plan_set_traffic_{plan_id}")],
        [InlineKeyboardButton(text=f"💰 قیمت: {price_text} تومان", callback_data=f"plan_set_price_{plan_id}")],
        [InlineKeyboardButton(text=f"📄 توضیحات: {description_text}", callback_data=f"plan_set_desc_{plan_id}")],
        [InlineKeyboardButton(text=f"🧩 سرویس: {service_text}", callback_data=f"plan_set_service_{plan_id}"), InlineKeyboardButton(text=f"🖧 سرور: {server_text}", callback_data=f"plan_set_servers_{plan_id}")],
        [InlineKeyboardButton(text=f"⚙️ وضعیت: {status_text}", callback_data=f"plan_toggle_{plan_id}")],
        [InlineKeyboardButton(text="✅ ذخیره تغییرات", callback_data=f"plan_save_{plan_id}"), InlineKeyboardButton(text="🗑️ حذف", callback_data=f"plan_delete_{plan_id}")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_plans")]
    ])


def get_plan_edit_keyboard(plan_id: int = None):
    p_id = plan_id if plan_id else "new"
    buttons = [
        [InlineKeyboardButton(text="📝 نام پلن", callback_data=f"plan_set_name_{p_id}"), InlineKeyboardButton(text="⏰ مدت زمان", callback_data=f"plan_set_days_{p_id}")],
        [InlineKeyboardButton(text="🌐 حجم ترافیک", callback_data=f"plan_set_traffic_{p_id}"), InlineKeyboardButton(text="💰 قیمت", callback_data=f"plan_set_price_{p_id}")],
        [InlineKeyboardButton(text="📄 توضیحات", callback_data=f"plan_set_desc_{p_id}")],
        [InlineKeyboardButton(text="🧩 نوع سرویس", callback_data=f"plan_set_service_{p_id}"), InlineKeyboardButton(text="🖧 سرورها", callback_data=f"plan_set_servers_{p_id}")]
    ]
    if plan_id:
        buttons.append([InlineKeyboardButton(text="✅ ذخیره تغییرات", callback_data=f"plan_save_{plan_id}")])
    else:
        buttons.append([InlineKeyboardButton(text="✅ ایجاد پلن جدید", callback_data="plan_save_new")])
    buttons.append([InlineKeyboardButton(text="🔙 انصراف", callback_data="admin_plans")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_buy_keyboard(plans: list):
    buttons = []
    for plan in plans:
        # Skip test account
        if plan.name == "اکانت تست":
            continue
        buttons.append([
            InlineKeyboardButton(
                text=f"🛒 {plan.name}",
                callback_data=f"buy_plan_{plan.id}"
            )
        ])
    if not buttons:
        buttons.append([InlineKeyboardButton(text="❌ پلنی یافت نشد", callback_data="back_to_main")])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_payment_method_keyboard(plan_id: int):
    """Keyboard for selecting payment method after selecting a plan."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 کارت به کارت", callback_data=f"pay_card_{plan_id}")],
        [InlineKeyboardButton(text="💰 کیف پول", callback_data=f"pay_wallet_{plan_id}")],
        [InlineKeyboardButton(text="🎁 کد تخفیف", callback_data=f"apply_discount_{plan_id}")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="buy"), InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="back_to_main")]
    ])


def get_payment_method_keyboard_for_renew(plan_id: int, config_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 کارت به کارت", callback_data=f"pay_card_{plan_id}_{config_id}")],
        [InlineKeyboardButton(text="💰 کیف پول", callback_data=f"pay_wallet_{plan_id}_{config_id}")],
        [InlineKeyboardButton(text="🎁 کد تخفیف", callback_data=f"apply_discount_{plan_id}_{config_id}")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data=f"cfg_view_{config_id}"), InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="back_to_main")]
    ])


def get_receipt_action_keyboard(receipt_id: int):
    """Keyboard for admin to approve/reject receipt."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ تایید پرداخت", callback_data=f"receipt_approve_{receipt_id}")],
        [InlineKeyboardButton(text="❌ رد پرداخت", callback_data=f"receipt_reject_{receipt_id}")]
    ])


def get_receipt_done_keyboard(status_text: str = "✅ انجام شد"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=status_text, callback_data="receipt_done")]
    ])




def get_admin_search_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 جستجوی کاربر", callback_data="admin_search_user")],
        [InlineKeyboardButton(text="🔗 جستجوی کانفیگ", callback_data="admin_search_config")],
        [InlineKeyboardButton(text="🏠 منوی مدیریت", callback_data="admin")],
    ])


def get_found_configs_keyboard(configs: list):
    buttons = []
    for cfg in configs:
        label = f"{cfg.client_ip} | {cfg.plan_name or 'بدون پلن'} | {cfg.user_telegram_id}"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"admin_cfg_view_{cfg.id}")])
    buttons.append([InlineKeyboardButton(text="🔍 جستجوی جدید", callback_data="admin_search"), InlineKeyboardButton(text="🏠 منوی مدیریت", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
def get_found_users_keyboard(users: list):
    buttons = []
    for user in users:
        name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "بدون نام"
        buttons.append([InlineKeyboardButton(text=f"{name} | {user.telegram_id}", callback_data=f"admin_user_{user.id}")])
    buttons.append([InlineKeyboardButton(text="🔍 جستجوی جدید", callback_data="admin_search"), InlineKeyboardButton(text="🏠 منوی مدیریت", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_user_manage_keyboard(
    user_id: int,
    telegram_id: int,
    full_name: str,
    username: str,
    wallet_balance: int,
    joined_date: str,
    is_member: bool,
    is_admin: bool,
    config_count: int,
    is_org: bool = False,
    is_blocked: bool = False,
    show_wallet_actions: bool = False,
    show_finance_panel: bool = False,
    total_traffic_text: str = "-",
    price_per_gb_text: str = "-",
    debt_text: str = "-",
    last_settlement_text: str = "-",
):
    org_label = "🏢 تبدیل به مشتری عادی" if is_org else "🏢 تبدیل به مشتری سازمانی"
    block_label = "✅ رفع مسدودی کاربر" if is_blocked else "⛔ مسدود کردن کاربر"

    buttons = [
        [InlineKeyboardButton(text=f"🆔 یوزر آیدی: {telegram_id}", callback_data="admin_user_info_ro")],
        [InlineKeyboardButton(text=f"👤 نام: {full_name}", callback_data="admin_user_info_ro")],
        [InlineKeyboardButton(text=f"📛 نام کاربری: {username}", callback_data="admin_user_info_ro")],
        [InlineKeyboardButton(text=f"💰 موجودی: {wallet_balance:,} تومان", callback_data=f"admin_user_wallet_actions_{user_id}")],
        [InlineKeyboardButton(text=f"📅 تاریخ عضویت: {joined_date}", callback_data="admin_user_info_ro")],
        [InlineKeyboardButton(text=f"🟢 وضعیت عضویت: {'فعال' if is_member else 'غیرفعال'}", callback_data="admin_user_info_ro")],
        [InlineKeyboardButton(text=f"⚙️ ادمین: {'بله' if is_admin else 'خیر'}", callback_data="admin_user_info_ro")],
        [InlineKeyboardButton(text=f"🔐 وضعیت دسترسی: {'مسدود' if is_blocked else 'فعال'}", callback_data="admin_user_info_ro")],
        [InlineKeyboardButton(text=f"🏢 نوع مشتری: {'سازمانی' if is_org else 'عادی'}", callback_data="admin_user_info_ro")],
        [InlineKeyboardButton(text=f"🔗 تعداد کانفیگ‌ها: {config_count}", callback_data="admin_user_info_ro")],
        [InlineKeyboardButton(text="🔗 مشاهده کانفیگ‌ها", callback_data=f"admin_user_configs_{user_id}")],
        [InlineKeyboardButton(text=block_label, callback_data=f"admin_user_block_toggle_{user_id}"), InlineKeyboardButton(text=org_label, callback_data=f"admin_user_org_toggle_{user_id}")],
    ]

    if show_wallet_actions:
        buttons.append([
            InlineKeyboardButton(text="➕ افزایش موجودی", callback_data=f"wallet_inc_{user_id}"),
            InlineKeyboardButton(text="➖ کاهش موجودی", callback_data=f"wallet_dec_{user_id}"),
        ])

    if is_org:
        buttons.append([InlineKeyboardButton(text="💼 مالی", callback_data=f"admin_user_finance_{user_id}")])
        if show_finance_panel:
            buttons.extend([
                [InlineKeyboardButton(text=f"📊 مجموع ترافیک مصرفی: {total_traffic_text}", callback_data=f"admin_user_org_total_traffic_{user_id}")],
                [InlineKeyboardButton(text=f"💰 هزینه هر گیگ: {price_per_gb_text}", callback_data=f"admin_user_org_price_edit_{user_id}")],
                [InlineKeyboardButton(text=f"🧾 مجموع قابل پرداخت: {debt_text}", callback_data=f"admin_user_org_debt_{user_id}")],
                [InlineKeyboardButton(text=f"🕓 تاریخ آخرین تسویه: {last_settlement_text}", callback_data=f"admin_user_org_last_settlement_{user_id}")],
                [InlineKeyboardButton(text="✅ تسویه", callback_data=f"admin_user_org_settle_{user_id}")],
            ])

    buttons.append([InlineKeyboardButton(text=" بازگشت به جستجو", callback_data="admin_search"), InlineKeyboardButton(text="🏠 منوی مدیریت", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_configs_keyboard(configs: list, is_org_customer: bool = False):
    buttons = []
    for config in configs:
        label = f"{config.plan_name or 'کانفیگ'} - {config.client_ip}"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"cfg_view_{config.id}")])
    if is_org_customer:
        buttons.append([
            InlineKeyboardButton(text="➕ ساخت اکانت", callback_data="org_create_account"),
            InlineKeyboardButton(text="💼 مالی", callback_data="org_finance"),
        ])
    buttons.append([InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_config_detail_keyboard(
    config_id: int,
    can_renew: bool = False,
    duration_days_text: str = "نامشخص",
    traffic_text: str = "نامشخص",
    consumed_text: str = "-",
    remaining_text: str = "-",
    status_text: str = "-",
):
    buttons = []
    renew_callback = f"cfg_renew_{config_id}" if can_renew else f"cfg_renew_unavailable_{config_id}"
    renew_label = "♻️ تمدید سرویس" if can_renew else "♻️ تمدید سرویس (پس از غیرفعال شدن)"
    buttons.append([InlineKeyboardButton(text=renew_label, callback_data=renew_callback)])
    buttons.append([InlineKeyboardButton(text=f"⏰ تعداد روز: {duration_days_text}", callback_data=f"admin_cfg_set_days_{config_id}")])
    buttons.append([InlineKeyboardButton(text=f"🌐 ترافیک کل: {traffic_text}", callback_data=f"admin_cfg_set_traffic_{config_id}")])
    buttons.append([InlineKeyboardButton(text=f"📊 ترافیک مصرفی: {consumed_text}", callback_data=f"admin_cfg_ro_{config_id}")])
    buttons.append([InlineKeyboardButton(text=f"📉 ترافیک باقی‌مانده: {remaining_text}", callback_data=f"admin_cfg_ro_{config_id}")])
    buttons.append([InlineKeyboardButton(text=f"🔘 وضعیت: {status_text}", callback_data=f"admin_cfg_ro_{config_id}")])
    buttons.append([InlineKeyboardButton(text="⏸️ غیرفعال کردن", callback_data=f"admin_cfg_disable_{config_id}"), InlineKeyboardButton(text="🗑️ حذف کانفیگ", callback_data=f"admin_cfg_delete_{config_id}")])
    buttons.append([InlineKeyboardButton(text=" بازگشت به کانفیگ‌ها", callback_data="configs"), InlineKeyboardButton(text="🏠 منوی مدیریت", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_config_confirm_delete_keyboard(config_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ بله، حذف کن", callback_data=f"admin_cfg_delete_confirm_{config_id}"), InlineKeyboardButton(text="❌ خیر", callback_data=f"admin_cfg_view_{config_id}")]
    ])


def get_config_detail_keyboard(
    config_id: int,
    can_renew: bool = False,
    is_org_customer: bool = False,
):
    """User view config detail keyboard"""
    buttons = []
    renew_callback = f"cfg_renew_{config_id}" if can_renew else f"cfg_renew_unavailable_{config_id}"
    renew_label = "♻️ تمدید سرویس" if can_renew else "♻️ تمدید سرویس (پس از غیرفعال شدن)"
    buttons.append([InlineKeyboardButton(text=renew_label, callback_data=renew_callback)])

    buttons.append([InlineKeyboardButton(text="🗑️ حذف کانفیگ", callback_data=f"cfg_delete_{config_id}")])

    if is_org_customer:
        buttons.append([InlineKeyboardButton(text="💼 موارد مالی", callback_data=f"cfg_financial_{config_id}")])

    buttons.append([InlineKeyboardButton(text="🔙 بازگشت به کانفیگ‌ها", callback_data="configs"), InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_user_config_confirm_delete_keyboard(config_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ بله، حذف کن", callback_data=f"cfg_delete_confirm_{config_id}"),
            InlineKeyboardButton(text="❌ خیر", callback_data=f"cfg_delete_cancel_{config_id}"),
        ]
    ])


def get_renew_confirmation_keyboard(config_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ بله، تمدید کن", callback_data=f"cfg_renew_force_yes_{config_id}"),
            InlineKeyboardButton(text="❌ خیر", callback_data="cfg_renew_force_no"),
        ]
    ])


def get_admin_user_configs_keyboard(user_id: int, configs: list):
    buttons = []
    for config in configs:
        label = f"{config.plan_name or 'کانفیگ'} - {config.client_ip}"
        status = "🟢" if config.status == "active" else "🔴"
        buttons.append([InlineKeyboardButton(text=f"{status} {label}", callback_data=f"admin_cfg_view_{config.id}")])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت به اطلاعات کاربر", callback_data=f"admin_user_{user_id}"), InlineKeyboardButton(text="🏠 منوی مدیریت", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_create_account_keyboard(plans: list):
    buttons = []
    for i in range(0, len(plans), 2):
        row = []
        plan1 = plans[i]
        row.append(InlineKeyboardButton(text=f"➕ {plan1.name} - {plan1.duration_days}روز", callback_data=f"create_acc_plan_{plan1.id}"))
        if i + 1 < len(plans):
            plan2 = plans[i + 1]
            row.append(InlineKeyboardButton(text=f"➕ {plan2.name} - {plan2.duration_days}روز", callback_data=f"create_acc_plan_{plan2.id}"))
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="📝 ایجاد پلن دلخواه", callback_data="create_acc_custom")])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_user_configs_keyboard(configs: list):
    buttons = []
    for cfg in configs:
        cfg_name = cfg.plan_name or f"WG-{cfg.client_ip}"
        buttons.append([InlineKeyboardButton(text=f"🔐 {cfg_name}", callback_data=f"mycfg_{cfg.id}")])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_user_config_detail_keyboard(config_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 دریافت فایل کانفیگ", callback_data=f"mycfg_file_{config_id}")],
        [InlineKeyboardButton(text="📷 دریافت QR Code", callback_data=f"mycfg_qr_{config_id}")],
        [InlineKeyboardButton(text="🔙 بازگشت به لیست کانفیگ‌ها", callback_data="configs")]
    ])


def get_profile_keyboard(
    first_name: str,
    username: str,
    wallet_balance: int,
    configs_count: int,
    active_configs: int,
    joined_date: str,
    member_status: str,
    is_org_customer: bool = False,
):
    username_text = f"@{username}" if username else "ندارد"
    buttons = [
        [InlineKeyboardButton(text=f"👤 نام: {first_name}", callback_data="profile_ro")],
        [InlineKeyboardButton(text=f"📛 نام کاربری: {username_text}", callback_data="profile_ro")],
        [InlineKeyboardButton(text=f"💰 موجودی کیف پول: {wallet_balance:,} تومان", callback_data="profile_ro")],
        [InlineKeyboardButton(text=f"🔐 تعداد کانفیگ‌ها: {configs_count}", callback_data="profile_ro")],
        [InlineKeyboardButton(text=f"✅ کانفیگ‌های فعال: {active_configs}", callback_data="profile_ro")],
        [InlineKeyboardButton(text=f"📅 تاریخ عضویت: {joined_date}", callback_data="profile_ro")],
        [InlineKeyboardButton(text=f"📌 وضعیت عضویت: {member_status}", callback_data="profile_ro")],
    ]
    if is_org_customer:
        buttons.append([InlineKeyboardButton(text="💼 موارد مالی", callback_data="profile_finance")])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)




def get_org_finance_keyboard(
    user_id: int,
    total_traffic_text: str,
    price_per_gb_text: str,
    debt_text: str,
    last_settlement_text: str,
    can_edit_price: bool = False,
    show_settlement_action: bool = False,
    back_callback: str = "profile",
):
    price_callback = f"admin_user_org_price_edit_{user_id}" if can_edit_price else "org_finance_ro"
    settle_callback = f"admin_user_org_settle_{user_id}" if can_edit_price else "org_settle_request"
    buttons = [
        [InlineKeyboardButton(text=f"📊 مجموع ترافیک مصرفی: {total_traffic_text}", callback_data="org_finance_ro")],
        [InlineKeyboardButton(text=f"💰 هزینه هر گیگ: {price_per_gb_text}", callback_data=price_callback)],
        [InlineKeyboardButton(text=f"🧾 مجموع قابل پرداخت: {debt_text}", callback_data="org_finance_ro")],
        [InlineKeyboardButton(text=f"🕓 تاریخ آخرین تسویه: {last_settlement_text}", callback_data="org_finance_ro")],
    ]
    if show_settlement_action:
        buttons.append([InlineKeyboardButton(text="✅ تسویه", callback_data=settle_callback)])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data=back_callback)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_profile_finance_keyboard(
    total_traffic_text: str,
    price_per_gb_text: str,
    debt_text: str,
    last_settlement_text: str,
):
    return get_org_finance_keyboard(
        user_id=0,
        total_traffic_text=total_traffic_text,
        price_per_gb_text=price_per_gb_text,
        debt_text=debt_text,
        last_settlement_text=last_settlement_text,
        can_edit_price=False,
        show_settlement_action=True,
        back_callback="profile",
    )


def get_wallet_keyboard(wallet_balance: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💰 موجودی کیف پول شما: {wallet_balance:,} تومان", callback_data="profile_ro")],
        [InlineKeyboardButton(text="➕ افزایش اعتبار", callback_data="wallet_topup")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")],
    ])


def get_admin_card_keyboard(card_number: str, card_holder: str):
    card_text = card_number if card_number else "هنوز شماره کارتی داده نشده"
    holder_text = card_holder if card_holder else "هنوز نام صاحب حساب ثبت نشده"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💳 شماره کارت: {card_text}", callback_data="admin_card_ro")],
        [InlineKeyboardButton(text=f"👤 نام صاحب حساب: {holder_text}", callback_data="admin_card_holder_ro")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin")],
    ])


def get_wallet_topup_amount_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 100,000 تومان", callback_data="wallet_amount_100000"), InlineKeyboardButton(text="💵 200,000 تومان", callback_data="wallet_amount_200000")],
        [InlineKeyboardButton(text="💵 500,000 تومان", callback_data="wallet_amount_500000"), InlineKeyboardButton(text="💵 1,000,000 تومان", callback_data="wallet_amount_1000000")],
        [InlineKeyboardButton(text="❌ انصراف", callback_data="wallet_topup_cancel")]
    ])


def get_cancel_payment_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ انصراف", callback_data="payment_cancel")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]
    ])


def get_service_types_keyboard(service_types: list):
    buttons = []
    for st in service_types:
        status = "🟢" if st.is_active else "🔴"
        buttons.append([InlineKeyboardButton(text=f"{status} {st.name} ({st.code})", callback_data=f"service_type_view_{st.id}")])
    buttons.append([InlineKeyboardButton(text="➕ افزودن نوع سرویس", callback_data="service_type_add")])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_servers_service_type_keyboard(service_types: list):
    buttons = [[InlineKeyboardButton(text=f"🧩 {st.name}", callback_data=f"admin_servers_type_{st.id}")] for st in service_types]
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _status_dot(value):
    if value is True:
        return "🟢"
    if value is False:
        return "🔴"
    return "⚪"


def get_servers_keyboard(server_rows: list, service_type_id: int, server_health_map: dict | None = None):
    buttons = []
    server_health_map = server_health_map or {}
    for srv in server_rows:
        health = server_health_map.get(srv.id)
        is_ok = bool(srv.is_active and health is True)
        status_dot = "🟢" if is_ok else "🔴"
        buttons.append([InlineKeyboardButton(text=f"{status_dot} {srv.name} ({srv.host})", callback_data=f"server_view_{srv.id}")])
    buttons.append([InlineKeyboardButton(text="➕ افزودن سرور", callback_data=f"server_add_{service_type_id}")])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_servers")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_server_detail_keyboard(server, service_type_id: int, field_statuses: dict | None = None):
    field_statuses = field_statuses or {}
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⚪ نام: {server.name}", callback_data=f"server_field_{server.id}_name")],
        [InlineKeyboardButton(text=f"{_status_dot(field_statuses.get('host'))} آی‌پی/هاست: {server.host}", callback_data=f"server_field_{server.id}_host")],
        [InlineKeyboardButton(text=f"⚪ پورت API: {server.api_port}", callback_data=f"server_field_{server.id}_api_port")],
        [InlineKeyboardButton(text=f"⚪ یوزرنیم: {server.username or '-'}", callback_data=f"server_field_{server.id}_username")],
        [InlineKeyboardButton(text=f"⚪ پسورد: {'***' if server.password else '-'}", callback_data=f"server_field_{server.id}_password")],
        [InlineKeyboardButton(text=f"{_status_dot(field_statuses.get('wg_interface'))} اینترفیس: {server.wg_interface or '-'}", callback_data=f"server_field_{server.id}_wg_interface")],
        [InlineKeyboardButton(text=f"⚪ Endpoint: {server.wg_server_endpoint or '-'}", callback_data=f"server_field_{server.id}_wg_server_endpoint")],
        [InlineKeyboardButton(text=f"⚪ Port WG: {server.wg_server_port or '-'}", callback_data=f"server_field_{server.id}_wg_server_port")],
        [InlineKeyboardButton(text=f"⚪ رنج IP کاربران: {server.wg_client_network_base or '-'}", callback_data=f"server_field_{server.id}_wg_client_network_base")],
        [InlineKeyboardButton(text=f"⚪ DNS: {server.wg_client_dns or '-'}", callback_data=f"server_field_{server.id}_wg_client_dns")],
        [InlineKeyboardButton(text=f"⚪ ظرفیت: {server.capacity}", callback_data=f"server_field_{server.id}_capacity")],
        [InlineKeyboardButton(text="🗑️ حذف", callback_data=f"server_delete_{server.id}")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data=f"admin_servers_type_{service_type_id}")],
    ])


def get_service_type_picker_keyboard(service_types: list, prefix: str):
    buttons = [[InlineKeyboardButton(text=st.name, callback_data=f"{prefix}{st.id}")] for st in service_types if st.is_active]
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_plans")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_plan_servers_picker_keyboard(servers: list, plan_id_token: str):
    buttons = [[InlineKeyboardButton(text=f"🖧 {s.name}", callback_data=f"plan_toggle_server_{plan_id_token}_{s.id}")] for s in servers]
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data=f"plan_back_service_select_{plan_id_token}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_plan_created_actions_keyboard(plan_id_token: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت مرحله قبل", callback_data=f"plan_back_service_select_{plan_id_token}")],
        [InlineKeyboardButton(text="🏠 بازگشت به منوی اصلی", callback_data="back_to_main")],
    ])


def get_plan_server_select_keyboard(servers: list, prefix: str):
    buttons = [[InlineKeyboardButton(text=f"🖧 {s.name}", callback_data=f"{prefix}{s.id}")] for s in servers]
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="buy")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_representatives_keyboard(representatives: list):
    buttons = [
        [InlineKeyboardButton(text="➕ افزودن نمایندگی", callback_data="rep_add")],
    ]
    for rep in representatives:
        status = "🟢" if rep.is_active else "🔴"
        buttons.append([InlineKeyboardButton(text=f"{status} {rep.name}", callback_data=f"rep_view_{rep.id}")])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_representative_action_keyboard(rep_id: int, is_active: bool):
    toggle_text = "⏸️ غیرفعال" if is_active else "▶️ فعال"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle_text, callback_data=f"rep_toggle_{rep_id}"), InlineKeyboardButton(text="🗑️ حذف", callback_data=f"rep_delete_{rep_id}")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_representatives")],
    ])
