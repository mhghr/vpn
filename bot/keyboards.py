from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_keyboard(is_admin_user: bool = False):
    buttons = [
        [InlineKeyboardButton(text="🛒 خرید", callback_data="buy"), InlineKeyboardButton(text="📱 نرم افزارها", callback_data="software")],
        [InlineKeyboardButton(text="🔗 کانفیگ ها", callback_data="configs"), InlineKeyboardButton(text="💰 شارژ کیف پول", callback_data="wallet")]
    ]
    if is_admin_user:
        buttons.append([InlineKeyboardButton(text="⚙️ مدیریت", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_keyboard(pending_panel=None):
    buttons = [
        [InlineKeyboardButton(text="🖥️ پنل‌ها", callback_data="admin_panels"), InlineKeyboardButton(text="🔍 جستجو", callback_data="admin_search_user")],
        [InlineKeyboardButton(text="📦 پلن ها", callback_data="admin_plans"), InlineKeyboardButton(text="💳 فیش‌های پرداخت", callback_data="admin_receipts")],
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
        # Show existing plans as buttons (one per row)
        for plan in plans:
            buttons.append([InlineKeyboardButton(text=f"{'✅' if plan.is_active else '❌'} {plan.name}", callback_data=f"plan_view_{plan.id}")])
    else:
        buttons.append([InlineKeyboardButton(text="📋 لیست پلن‌ها", callback_data="plan_list")])
    
    buttons.append([InlineKeyboardButton(text="➕ افزودن پلن جدید", callback_data="plan_create")])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_plan_list_keyboard(plans: list):
    buttons = []
    for i in range(0, len(plans), 2):
        row = []
        plan1 = plans[i]
        row.append(InlineKeyboardButton(text=f"{'✅' if plan1.is_active else '❌'} {plan1.name}", callback_data=f"plan_view_{plan1.id}"))
        if i + 1 < len(plans):
            plan2 = plans[i + 1]
            row.append(InlineKeyboardButton(text=f"{'✅' if plan2.is_active else '❌'} {plan2.name}", callback_data=f"plan_view_{plan2.id}"))
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="➕ پلن جدید", callback_data="plan_create"), InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_plans")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_plan_action_keyboard(plan_id: int, is_active: bool = True):
    status_text = "❌ غیرفعال" if is_active else "✅ فعال"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ ویرایش", callback_data=f"plan_edit_{plan_id}"), InlineKeyboardButton(text=status_text, callback_data=f"plan_toggle_{plan_id}")],
        [InlineKeyboardButton(text="🗑️ حذف", callback_data=f"plan_delete_{plan_id}"), InlineKeyboardButton(text="📋 لیست", callback_data="plan_list")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_plans")]
    ])


def get_plan_edit_keyboard(plan_id: int = None):
    p_id = plan_id if plan_id else "new"
    buttons = [
        [InlineKeyboardButton(text="📝 نام پلن", callback_data=f"plan_set_name_{p_id}"), InlineKeyboardButton(text="⏰ روز", callback_data=f"plan_set_days_{p_id}")],
        [InlineKeyboardButton(text="🌐 گیگ", callback_data=f"plan_set_traffic_{p_id}"), InlineKeyboardButton(text="💰 قیمت", callback_data=f"plan_set_price_{p_id}")],
        [InlineKeyboardButton(text="📄 توضیحات", callback_data=f"plan_set_desc_{p_id}")]
    ]
    if plan_id:
        buttons.append([InlineKeyboardButton(text="✅ ذخیره پلن", callback_data=f"plan_save_{plan_id}")])
    else:
        buttons.append([InlineKeyboardButton(text="✅ ذخیره پلن جدید", callback_data="plan_save_new")])
    buttons.append([InlineKeyboardButton(text="🔙 انصراف", callback_data="admin_plans")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_buy_keyboard(plans: list):
    buttons = []
    for i in range(0, len(plans), 2):
        row = []
        plan1 = plans[i]
        row.append(InlineKeyboardButton(text=f"{plan1.name} - {plan1.duration_days}روز", callback_data=f"buy_plan_{plan1.id}"))
        if i + 1 < len(plans):
            plan2 = plans[i + 1]
            row.append(InlineKeyboardButton(text=f"{plan2.name} - {plan2.duration_days}روز", callback_data=f"buy_plan_{plan2.id}"))
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_payment_method_keyboard(plan_id: int):
    """Keyboard for selecting payment method after selecting a plan."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 کارت به کارت", callback_data=f"pay_card_{plan_id}")],
        [InlineKeyboardButton(text="💰 کیف پول", callback_data=f"pay_wallet_{plan_id}")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="buy")]
    ])


def get_receipt_action_keyboard(receipt_id: int):
    """Keyboard for admin to approve/reject receipt."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ تایید پرداخت", callback_data=f"receipt_approve_{receipt_id}")],
        [InlineKeyboardButton(text="❌ رد پرداخت", callback_data=f"receipt_reject_{receipt_id}")]
    ])


def get_create_account_keyboard(plans: list):
    """Keyboard for admin to select a plan for account creation."""
    buttons = []
    for i in range(0, len(plans), 2):
        row = []
        plan1 = plans[i]
        row.append(InlineKeyboardButton(text=f"{plan1.name} - {plan1.duration_days}روز", callback_data=f"create_acc_plan_{plan1.id}"))
        if i + 1 < len(plans):
            plan2 = plans[i + 1]
            row.append(InlineKeyboardButton(text=f"{plan2.name} - {plan2.duration_days}روز", callback_data=f"create_acc_plan_{plan2.id}"))
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="📝 پلن دلخواه", callback_data="create_acc_custom")])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
