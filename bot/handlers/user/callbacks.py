from ..common import *

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
                f"📊 مجموع ترافیک لینک‌های فعال: {financials['total_traffic_gb']:.2f} GB\n"
                f"💰 هزینه هر گیگ: {financials['price_per_gb']:,} تومان\n"
                f"🧾 مبلغ بدهکاری: {financials['debt_amount']:,} تومان\n"
                f"🕓 زمان آخرین تسویه: {financials['last_settlement']}"
            )
            await callback.answer(finance_text, show_alert=True)
        finally:
            db.close()

    elif data == "profile_ro" or data == "profile_finance_ro":
        await callback.answer("این بخش فقط خواندنی است.", show_alert=False)

    elif data == "profile_finance":
        db = SessionLocal()
        try:
            user = get_user(db, str(user_id))
            if not user or not user.is_organization_customer:
                await callback.answer("اطلاعات مالی برای این حساب فعال نیست.", show_alert=True)
                return
            financials = calculate_org_user_financials(db, user)
            await callback.message.answer(
                "💼 موارد مالی مشتری سازمانی (فقط خواندنی):",
                reply_markup=get_profile_finance_keyboard(
                    total_traffic_text=f"{financials['total_traffic_gb']:.2f} GB",
                    price_per_gb_text=f"{financials['price_per_gb']:,} تومان",
                    debt_text=f"{financials['debt_amount']:,} تومان",
                    last_settlement_text=financials['last_settlement'],
                ),
                parse_mode="HTML",
            )
        finally:
            db.close()

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
            balance = (user.wallet_balance if user else 0)
            await callback.message.answer("‌", reply_markup=get_wallet_keyboard(balance), parse_mode="HTML")
        finally:
            db.close()

    elif data == "wallet_topup":
        db = SessionLocal()
        try:
            user = get_user(db, str(user_id))
            balance = user.wallet_balance if user else 0
            card_number, _card_holder = get_card_info()
            card_text = card_number if card_number else "هنوز شماره کارتی داده نشده"
            user_payment_state[user_id] = {"method": "wallet_topup", "step": "amount_input"}
            await callback.message.answer(
                f"💳 افزایش اعتبار کیف پول\n\n💰 موجودی کیف پول شما: {balance:,} تومان\n\nبرای افزایش اعتبار لطفا مبلغ مورد نظر را به شماره کارت زیر واریز نمایید و عکس فیش واریز را در این مرحله آپلود کنید.\n\n🪪 شماره کارت:\n<code>{card_text}</code>\n\nابتدا مبلغ را به تومان ارسال کنید:",
                parse_mode="HTML"
            )
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
                await callback.message.answer(
                    "👤 حساب کاربری\n\nبرای مشاهده جزئیات، از دکمه‌های فقط‌خواندنی زیر استفاده کنید:",
                    reply_markup=get_profile_keyboard(
                        first_name=user.first_name or "-",
                        username=user.username,
                        wallet_balance=user.wallet_balance,
                        configs_count=configs_count,
                        active_configs=active_configs,
                        joined_date=joined_date,
                        member_status=member_status,
                        is_org_customer=bool(user.is_organization_customer),
                    ),
                    parse_mode="HTML",
                )
            else:
                await callback.message.answer("❌ کاربر یافت نشد.", parse_mode="HTML")
        finally:
            db.close()

    else:
        return False
    return True
