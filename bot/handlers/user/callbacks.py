from ..common import *
from .profile import handle_user_profile_callbacks

async def handle_user_callbacks(callback: CallbackQuery, bot, data: str, user_id: int) -> bool:
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
                if not server:
                    await callback.message.answer("❌ برای پلن اکانت تست هیچ سرور فعالی در دیتابیس مپ نشده است.", parse_mode="HTML")
                    return
                wg_result = wireguard.create_wireguard_account(**build_wg_kwargs(server, str(user_id), plan, plan.name, plan.duration_days))
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
                        f"🏷 نام کانفیگ: {wg_result.get('peer_comment', 'نامشخص')}\n"
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

    elif data == "configs":
        db = SessionLocal()
        try:
            configs = db.query(WireGuardConfig).filter(
                WireGuardConfig.user_telegram_id == str(user_id)
            ).order_by(WireGuardConfig.created_at.desc()).all()
            user_obj = get_user(db, str(user_id))
            is_org_customer = bool(user_obj and user_obj.is_organization_customer)
            if configs:
                await callback.message.answer(
                    "🔗 کانفیگ های من\n\nبرای مشاهده جزئیات، کانفیگ موردنظر را انتخاب کنید:",
                    reply_markup=get_configs_keyboard(configs, is_org_customer=is_org_customer),
                    parse_mode="HTML"
                )
            elif is_org_customer:
                await callback.message.answer(
                    "🔗 هنوز کانفیگی ندارید. می‌توانید از دکمه‌های زیر استفاده کنید:",
                    reply_markup=get_configs_keyboard([], is_org_customer=True),
                    parse_mode="HTML"
                )
            else:
                await callback.message.answer(MY_CONFIGS_MESSAGE, parse_mode="HTML")
        finally:
            db.close()

    elif data == "org_create_account":
        db = SessionLocal()
        try:
            user_obj = get_user(db, str(user_id))
            if not user_obj or not user_obj.is_organization_customer:
                await callback.answer("این گزینه فقط برای مشتری سازمانی فعال است.", show_alert=True)
                return
            org_user_state[user_id] = {"step": "name"}
            await callback.message.answer("ابتدا یک نام برای اکانت وارد کنید:", parse_mode="HTML")
        finally:
            db.close()

    elif data == "org_finance":
        db = SessionLocal()
        try:
            user_obj = get_user(db, str(user_id))
            if not user_obj or not user_obj.is_organization_customer:
                await callback.answer("اطلاعات مالی برای این حساب فعال نیست.", show_alert=True)
                return
            financials = calculate_org_user_financials(db, user_obj)
            await callback.message.answer(
                "💼 مالی مشتری سازمانی:",
                reply_markup=get_org_finance_keyboard(
                    user_id=0,
                    total_traffic_text=f"{financials['total_traffic_gb']:.2f} GB",
                    price_per_gb_text=f"{financials['price_per_gb']:,} تومان",
                    debt_text=f"{financials['debt_amount']:,} تومان",
                    last_settlement_text=financials['last_settlement'],
                    can_edit_price=False,
                    show_settlement_action=True,
                    back_callback="configs",
                ),
                parse_mode="HTML",
            )
        finally:
            db.close()

    elif data == "org_settle_request":
        db = SessionLocal()
        try:
            user_obj = get_user(db, str(user_id))
            if not user_obj or not user_obj.is_organization_customer:
                await callback.answer("این گزینه فقط برای مشتری سازمانی فعال است.", show_alert=True)
                return
            financials = calculate_org_user_financials(db, user_obj)
            card_number, card_holder = get_card_info()
            org_user_state[user_id] = {"step": "settlement_receipt", "amount": financials["debt_amount"]}
            await callback.message.answer(
                (
                    "✅ درخواست تسویه ثبت شد.\n"
                    f"مبلغ قابل پرداخت: {financials['debt_amount']:,} تومان\n\n"
                    "لطفاً مبلغ را به کارت زیر واریز کنید و سپس عکس فیش را ارسال کنید:\n"
                    f"<code>{card_number or '-'}</code>\n{card_holder or '-'}"
                ),
                parse_mode="HTML",
            )
        finally:
            db.close()

    elif data == "org_finance_ro":
        await callback.answer("این بخش فقط جهت نمایش است.", show_alert=False)

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

            plan = db.query(Plan).filter(Plan.id == config.plan_id).first() if config.plan_id else None
            plan_traffic_bytes, remaining_bytes = get_config_remaining_bytes(config, plan)
            consumed_bytes = get_config_consumed_bytes(config)
            expires_at = get_config_expires_at(config, plan)
            duration_days, traffic_limit_gb = get_config_limits(config, plan)

            can_renew = can_renew_config_now(config, plan)
            server = db.query(Server).filter(Server.id == config.server_id).first() if config.server_id else None
            remaining_days = "نامشخص"
            if expires_at:
                remaining_days = str(max(int((expires_at - datetime.utcnow()).total_seconds() // 86400), 0))

            msg = (
                "📋 جزئیات کانفیگ\n\n"
                f"• پلن: {config.plan_name or 'بدون پلن'}\n"
                f"• سرور: {server.name if server else '-'}\n"
                f"• آی پی: {config.client_ip}\n"
                f"• زمان ایجاد: {format_jalali_date(config.created_at)}\n"
                f"• آخرین تمدید: {format_jalali_date(config.renewed_at)}\n"
                f"• تعداد روز: {duration_days if duration_days is not None else 'نامشخص'}\n"
                f"• ترافیک کل: {traffic_limit_gb if traffic_limit_gb is not None else 'نامشخص'} گیگ\n"
                f"• تاریخ انقضا: {format_jalali_date(expires_at)}\n"
                f"• وضعیت: {'🔴 غیرفعال' if config.status != 'active' else '🟢 فعال'}\n"
                f"• ترافیک مصرفی: {format_traffic_size(consumed_bytes)}\n"
                f"• ترافیک باقی‌مانده: {format_traffic_size(remaining_bytes) if plan_traffic_bytes else 'نامحدود/نامشخص'}\n"
                f"• روز باقی‌مانده: {remaining_days}"
            )
            owner_user = db.query(User).filter(User.telegram_id == config.user_telegram_id).first()
            is_org_customer = bool(owner_user and owner_user.is_organization_customer)
            await callback.message.answer(
                msg,
                reply_markup=get_config_detail_keyboard(
                    config.id,
                    can_renew=can_renew,
                    is_org_customer=is_org_customer,
                ),
                parse_mode="HTML"
            )
        finally:
            db.close()

    elif data == "admin_user_info_ro":
        await callback.answer("این بخش فقط جهت نمایش است.", show_alert=False)


    elif data.startswith("cfg_delete_confirm_"):
        config_id = int(data.replace("cfg_delete_confirm_", ""))
        db = SessionLocal()
        try:
            cfg = db.query(WireGuardConfig).filter(WireGuardConfig.id == config_id, WireGuardConfig.user_telegram_id == str(user_id)).first()
            if not cfg:
                await callback.message.answer("❌ کانفیگ یافت نشد.", parse_mode="HTML")
                return

            consumed_bytes = (cfg.cumulative_rx_bytes or 0) + (cfg.cumulative_tx_bytes or 0)
            consumed_gb = consumed_bytes / (1024 ** 3)

            owner_user = db.query(User).filter(User.telegram_id == cfg.user_telegram_id).first()
            if owner_user and owner_user.is_organization_customer and consumed_bytes > 0:
                owner_user.org_deleted_traffic_bytes = (owner_user.org_deleted_traffic_bytes or 0) + consumed_bytes

            db.delete(cfg)
            db.commit()

            if owner_user and owner_user.is_organization_customer:
                await callback.message.answer(
                    f"✅ لینک حذف شد و مقدار {consumed_gb:.2f} گیگ ترافیک این لینک در فاکتور لحاظ خواهد شد.",
                    parse_mode="HTML"
                )
            else:
                await callback.message.answer("✅ کانفیگ حذف شد.", parse_mode="HTML")
        finally:
            db.close()

    elif data.startswith("cfg_delete_cancel_"):
        await callback.message.answer("❎ حذف لینک لغو شد.", parse_mode="HTML")

    elif data.startswith("cfg_delete_"):
        config_id = int(data.replace("cfg_delete_", ""))
        db = SessionLocal()
        try:
            cfg = db.query(WireGuardConfig).filter(WireGuardConfig.id == config_id, WireGuardConfig.user_telegram_id == str(user_id)).first()
            if not cfg:
                await callback.message.answer("❌ کانفیگ یافت نشد.", parse_mode="HTML")
                return
            await callback.message.answer(
                "⚠️ مطمئن هستید که می‌خواهید این لینک را حذف کنید؟",
                reply_markup=get_user_config_confirm_delete_keyboard(config_id),
                parse_mode="HTML"
            )
        finally:
            db.close()

    elif data.startswith("cfg_financial_"):
        config_id = int(data.replace("cfg_financial_", ""))
        db = SessionLocal()
        try:
            config = db.query(WireGuardConfig).filter(WireGuardConfig.id == config_id).first()
            if not config:
                await callback.answer("کانفیگ یافت نشد.", show_alert=True)
                return
            if str(user_id) != config.user_telegram_id and not is_admin(user_id):
                await callback.answer("شما دسترسی ندارید.", show_alert=True)
                return
            owner_user = db.query(User).filter(User.telegram_id == config.user_telegram_id).first()
            if not owner_user or not owner_user.is_organization_customer:
                await callback.answer("این کانفیگ اطلاعات مالی سازمانی ندارد.", show_alert=True)
                return
            financials = calculate_org_user_financials(db, owner_user)
            finance_text = (
                f"📊 مجموع ترافیک قابل‌فاکتور (فعال + حذف‌شده): {financials['total_traffic_gb']:.2f} GB\n"
                f"💰 هزینه هر گیگ: {financials['price_per_gb']:,} تومان\n"
                f"🧾 مبلغ بدهکاری: {financials['debt_amount']:,} تومان\n"
                f"🕓 زمان آخرین تسویه: {financials['last_settlement']}"
            )
            await callback.answer(finance_text, show_alert=True)
        finally:
            db.close()

    elif await handle_user_profile_callbacks(callback, bot, data, user_id):
        return True

    else:
        return False
    return True
