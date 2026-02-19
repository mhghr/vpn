from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_keyboard(is_admin_user: bool = False):
    buttons = [
        [InlineKeyboardButton(text="🛒 خرید", callback_data="buy"), InlineKeyboardButton(text="📱 نرم‌افزارها", callback_data="software")],
        [InlineKeyboardButton(text="🔗 کانفیگ ها", callback_data="configs"), InlineKeyboardButton(text="💰 شارژ کیف پول", callback_data="wallet")],
        [InlineKeyboardButton(text="🧪 اکانت تست", callback_data="test_account_create")]
    ]
    if is_admin_user:
        buttons.append([InlineKeyboardButton(text="⚙️ مدیریت", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_keyboard(pending_panel=None):
    buttons = [
        [InlineKeyboardButton(text="🖥️ پنل‌ها", callback_data="admin_panels"), InlineKeyboardButton(text="🔍 جستجو", callback_data="admin_search_user")],
        [InlineKeyboardButton(text="📦 پلن ها", callback_data="admin_plans"), InlineKeyboardButton(text="💳 فیش‌های پرداخت", callback_data="admin_receipts")],
        [InlineKeyboardButton(text="🎁 کد تخفیف", callback_data="admin_discount_create")],
        [InlineKeyboardButton(text="🔗 ساخت اکانت", callback_data="admin_create_account")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]
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
            status_emoji = "🟢" if plan.is_active else "🔴"
            buttons.append([InlineKeyboardButton(text=f"{status_emoji} {plan.name}", callback_data=f"plan_view_{plan.id}")])
    else:
        buttons.append([InlineKeyboardButton(text="📋 لیست پلن‌ها", callback_data="plan_list")])
    
    buttons.append([InlineKeyboardButton(text="🧪 اکانت تست", callback_data="test_plan_manage")])
    buttons.append([InlineKeyboardButton(text="➕ افزودن پلن جدید", callback_data="plan_create")])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_plan_list_keyboard(plans: list):
    buttons = []
    for i in range(0, len(plans), 2):
        row = []
        plan1 = plans[i]
        status_emoji = "🟢" if plan1.is_active else "🔴"
        row.append(InlineKeyboardButton(text=f"{status_emoji} {plan1.name}", callback_data=f"plan_view_{plan1.id}"))
        if i + 1 < len(plans):
            plan2 = plans[i + 1]
            status_emoji2 = "🟢" if plan2.is_active else "🔴"
            row.append(InlineKeyboardButton(text=f"{status_emoji2} {plan2.name}", callback_data=f"plan_view_{plan2.id}"))
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="➕ پلن جدید", callback_data="plan_create"), InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_plans")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_plan_action_keyboard(plan_id: int, is_active: bool = True):
    status_emoji = "🔴 غیرفعال" if is_active else "🟢 فعال"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ ویرایش", callback_data=f"plan_edit_{plan_id}"), InlineKeyboardButton(text=status_emoji, callback_data=f"plan_toggle_{plan_id}")],
        [InlineKeyboardButton(text="🗑️ حذف", callback_data=f"plan_delete_{plan_id}"), InlineKeyboardButton(text="📋 لیست", callback_data="plan_list")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_plans")]
    ])


def get_plan_edit_keyboard(plan_id: int = None):
    p_id = plan_id if plan_id else "new"
    buttons = [
        [InlineKeyboardButton(text="📝 نام پلن", callback_data=f"plan_set_name_{p_id}"), InlineKeyboardButton(text="⏰ مدت زمان", callback_data=f"plan_set_days_{p_id}")],
        [InlineKeyboardButton(text="🌐 حجم ترافیک", callback_data=f"plan_set_traffic_{p_id}"), InlineKeyboardButton(text="💰 قیمت", callback_data=f"plan_set_price_{p_id}")],
        [InlineKeyboardButton(text="📄 توضیحات", callback_data=f"plan_set_desc_{p_id}")]
    ]
    if plan_id:
        buttons.append([InlineKeyboardButton(text="✅ ذخیره تغییرات", callback_data=f"plan_save_{plan_id}")])
    else:
        buttons.append([InlineKeyboardButton(text="✅ ایجاد پلن جدید", callback_data="plan_save_new")])
    buttons.append([InlineKeyboardButton(text="🔙 انصراف", callback_data="admin_plans")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_buy_keyboard(plans: list):
    buttons = []
    for i in range(0, len(plans), 2):
        row = []
        plan1 = plans[i]
        row.append(InlineKeyboardButton(text=f"🔥 {plan1.name} - {plan1.duration_days} روز", callback_data=f"buy_plan_{plan1.id}"))
        if i + 1 < len(plans):
            plan2 = plans[i + 1]
            row.append(InlineKeyboardButton(text=f"🔥 {plan2.name} - {plan2.duration_days} روز", callback_data=f"buy_plan_{plan2.id}"))
        buttons.append(row)
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


def get_receipt_done_keyboard(status_text: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=status_text, callback_data="receipt_done")]
    ])


def get_found_users_keyboard(users: list):
    buttons = []
    for user in users[:20]:
        name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "بدون نام"
        buttons.append([InlineKeyboardButton(text=f"{name} | {user.telegram_id}", callback_data=f"admin_user_{user.id}")])
    buttons.append([InlineKeyboardButton(text="🔍 جستجوی جدید", callback_data="admin_search_user"), InlineKeyboardButton(text="🏠 منوی مدیریت", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_user_manage_keyboard(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ افزایش موجودی", callback_data=f"wallet_inc_{user_id}"), InlineKeyboardButton(text="➖ کاهش موجودی", callback_data=f"wallet_dec_{user_id}")],
        [InlineKeyboardButton(text="🔗 مشاهده کانفیگ‌ها", callback_data=f"admin_user_configs_{user_id}")],
        [InlineKeyboardButton(text=" بازگشت به جستجو", callback_data="admin_search_user"), InlineKeyboardButton(text="🏠 منوی مدیریت", callback_data="admin")]
    ])


def get_configs_keyboard(configs: list):
    buttons = []
    for config in configs:
        label = f"{config.plan_name or 'کانفیگ'} - {config.client_ip}"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"cfg_view_{config.id}")])
    buttons.append([InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_config_detail_keyboard(config_id: int, can_renew: bool = False):
    buttons = []
    if can_renew:
        buttons.append([InlineKeyboardButton(text="♻️ تمدید سرویس", callback_data=f"cfg_renew_{config_id}")])
    buttons.append([InlineKeyboardButton(text="⏸️ غیرفعال کردن", callback_data=f"admin_cfg_disable_{config_id}"), InlineKeyboardButton(text="🗑️ حذف کانفیگ", callback_data=f"admin_cfg_delete_{config_id}")])
    buttons.append([InlineKeyboardButton(text=" بازگشت به کانفیگ‌ها", callback_data="configs"), InlineKeyboardButton(text="🏠 منوی مدیریت", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_config_confirm_delete_keyboard(config_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ بله، حذف کن", callback_data=f"admin_cfg_delete_confirm_{config_id}"), InlineKeyboardButton(text="❌ خیر", callback_data=f"admin_cfg_view_{config_id}")]
    ])


def get_config_detail_keyboard(config_id: int, can_renew: bool = False):
    """User view config detail keyboard"""
    buttons = []
    if can_renew:
        buttons.append([InlineKeyboardButton(text="♻️ تمدید سرویس", callback_data=f"cfg_renew_{config_id}")])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت به کانفیگ‌ها", callback_data="configs"), InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


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


def get_wallet_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ شارژ کیف پول", callback_data="wallet_topup")],
        [InlineKeyboardButton(text="👤 حساب کاربری", callback_data="profile"), InlineKeyboardButton(text="🛒 خرید پلن", callback_data="buy")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]
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


def get_test_plan_manage_keyboard(test_plan_id: int, is_active: bool):
    toggle_text = "🟢 فعال کردن" if not is_active else "🔴 غیرفعال کردن"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏰ تنظیم مدت زمان", callback_data=f"test_plan_set_days_{test_plan_id}"), InlineKeyboardButton(text="🌐 تنظیم ترافیک", callback_data=f"test_plan_set_traffic_{test_plan_id}")],
        [InlineKeyboardButton(text=toggle_text, callback_data=f"test_plan_toggle_{test_plan_id}")],
        [InlineKeyboardButton(text="🔙 بازگشت به پلن‌ها", callback_data="admin_plans")]
    ])
