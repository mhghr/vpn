from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def get_main_keyboard(is_admin_user: bool = False):
    buttons = [
        [KeyboardButton(text="🛒 خرید جدید"), KeyboardButton(text="📱 نرم‌افزارها")],
        [KeyboardButton(text="🔗 کانفیگ‌های من"), KeyboardButton(text="📖 آموزش اتصال")],
        [KeyboardButton(text="📚 آموزش"), KeyboardButton(text="💰 کیف پول")],
        [KeyboardButton(text="🧪 اکانت تست")],
        [KeyboardButton(text="👤 حساب کاربری")],
    ]
    if is_admin_user:
        buttons.append([KeyboardButton(text="⚙️ مدیریت")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def get_admin_keyboard(pending_panel=None):
    buttons = []
    if pending_panel:
        buttons.append([KeyboardButton(text="🔔 درخواست پنل جدید")])
    buttons.extend([
        [KeyboardButton(text="🖥️ پنل‌ها"), KeyboardButton(text="🔍 جستجو")],
        [KeyboardButton(text="📦 پلن ها"), KeyboardButton(text="💳 فیش‌های پرداخت")],
        [KeyboardButton(text="🎁 کد تخفیف"), KeyboardButton(text="🧩 انواع سرویس")],
        [KeyboardButton(text="🖧 مدیریت سرورها"), KeyboardButton(text="🔗 ساخت اکانت")],
        [KeyboardButton(text="🤝 نمایندگی‌ها"), KeyboardButton(text="📚 آموزش ادمین")],
        [KeyboardButton(text="🔙 بازگشت")],
    ])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


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
    
    buttons.append([InlineKeyboardButton(text="➕ افزودن پلن جدید", callback_data="plan_create")])
    buttons.append([InlineKeyboardButton(text="🧪 اکانت تست", callback_data="plan_test_account")])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_plan_list_keyboard(plans: list):
    buttons = []
    for plan in plans:
        status_emoji = "🟢" if plan.is_active else "🔴"
        buttons.append([InlineKeyboardButton(text=f"{status_emoji} {plan.name}", callback_data=f"plan_view_{plan.id}")])
    buttons.append([InlineKeyboardButton(text="➕ پلن جدید", callback_data="plan_create")])
    buttons.append([InlineKeyboardButton(text="🧪 اکانت تست", callback_data="plan_test_account")])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_plans")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)




def get_test_account_keyboard(has_plan: bool):
    edit_label = "✏️ ویرایش اکانت تست" if has_plan else "➕ ایجاد اکانت تست"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=edit_label, callback_data="plan_test_account_edit")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_plans")]
    ])

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
                [InlineKeyboardButton(text=f"📊 مجموع ترافیک لینک‌های فعال: {total_traffic_text}", callback_data=f"admin_user_org_total_traffic_{user_id}")],
                [InlineKeyboardButton(text=f"💰 هزینه هر گیگ: {price_per_gb_text}", callback_data=f"admin_user_org_price_{user_id}")],
                [InlineKeyboardButton(text=f"🧾 مبلغ بدهکاری: {debt_text}", callback_data=f"admin_user_org_debt_{user_id}")],
                [InlineKeyboardButton(text=f"🕓 زمان آخرین تسویه: {last_settlement_text}", callback_data=f"admin_user_org_last_settlement_{user_id}")],
                [InlineKeyboardButton(text="✅ تسویه حساب انجام شد", callback_data=f"admin_user_org_settle_{user_id}")],
            ])

    buttons.append([InlineKeyboardButton(text=" بازگشت به جستجو", callback_data="admin_search_user"), InlineKeyboardButton(text="🏠 منوی مدیریت", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_configs_keyboard(configs: list):
    buttons = []
    for config in configs:
        label = f"{config.plan_name or 'کانفیگ'} - {config.client_ip}"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"cfg_view_{config.id}")])
    buttons.append([InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_config_detail_keyboard(config_id: int, can_renew: bool = False):
    buttons = []
    renew_callback = f"cfg_renew_{config_id}" if can_renew else f"cfg_renew_unavailable_{config_id}"
    renew_label = "♻️ تمدید سرویس" if can_renew else "♻️ تمدید سرویس (پس از غیرفعال شدن)"
    buttons.append([InlineKeyboardButton(text=renew_label, callback_data=renew_callback)])
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
    total_traffic_text: str = "-",
    price_per_gb_text: str = "-",
    debt_text: str = "-",
    last_settlement_text: str = "-",
):
    """User view config detail keyboard"""
    buttons = []
    renew_callback = f"cfg_renew_{config_id}" if can_renew else f"cfg_renew_unavailable_{config_id}"
    renew_label = "♻️ تمدید سرویس" if can_renew else "♻️ تمدید سرویس (پس از غیرفعال شدن)"
    buttons.append([InlineKeyboardButton(text=renew_label, callback_data=renew_callback)])

    if is_org_customer:
        buttons.extend([
            [InlineKeyboardButton(text=f"📊 مجموع ترافیک لینک‌های فعال: {total_traffic_text}", callback_data="cfg_enterprise_ro_traffic")],
            [InlineKeyboardButton(text=f"💰 هزینه هر گیگ: {price_per_gb_text}", callback_data="cfg_enterprise_ro_price")],
            [InlineKeyboardButton(text="✅ تسویه حساب: فقط توسط ادمین", callback_data="cfg_enterprise_ro_settle")],
            [InlineKeyboardButton(text=f"🧾 مبلغ بدهکاری: {debt_text}", callback_data="cfg_enterprise_ro_debt")],
            [InlineKeyboardButton(text=f"🕓 آخرین تسویه: {last_settlement_text}", callback_data="cfg_enterprise_ro_last_settlement")],
        ])

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


def get_servers_keyboard(server_rows: list, service_type_id: int):
    buttons = []
    for srv in server_rows:
        status = "🟢" if srv.is_active else "🔴"
        buttons.append([InlineKeyboardButton(text=f"{status} {srv.name} ({srv.host})", callback_data=f"server_view_{srv.id}")])
    buttons.append([InlineKeyboardButton(text="➕ افزودن سرور", callback_data=f"server_add_{service_type_id}")])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_servers")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_server_action_keyboard(server_id: int, service_type_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ ویرایش", callback_data=f"server_edit_{server_id}"), InlineKeyboardButton(text="🗑️ حذف", callback_data=f"server_delete_{server_id}")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data=f"admin_servers_type_{service_type_id}")]
    ])


def get_service_type_picker_keyboard(service_types: list, prefix: str):
    buttons = [[InlineKeyboardButton(text=st.name, callback_data=f"{prefix}{st.id}")] for st in service_types if st.is_active]
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_plans")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_plan_servers_picker_keyboard(servers: list, plan_id_token: str):
    buttons = [[InlineKeyboardButton(text=f"🖧 {s.name}", callback_data=f"plan_toggle_server_{plan_id_token}_{s.id}")] for s in servers]
    buttons.append([InlineKeyboardButton(text="✅ پایان انتخاب", callback_data=f"plan_servers_done_{plan_id_token}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


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
