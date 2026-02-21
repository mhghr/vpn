from ..common import *

async def handle_admin_callbacks(callback: CallbackQuery, bot, data: str, user_id: int) -> bool:
    if data == "admin":
        pending_panel = load_pending_panel()
        await callback.message.answer(ADMIN_MESSAGE, reply_markup=get_admin_keyboard(pending_panel), parse_mode="HTML")

    elif data == "admin_card_settings":
        card_number, _card_holder = get_card_info()
        await callback.message.answer("💳 مدیریت شماره کارت", reply_markup=get_admin_card_keyboard(card_number), parse_mode="HTML")

    elif data == "admin_card_ro":
        await callback.answer("این مورد فقط نمایشی است.", show_alert=False)

    elif data == "admin_card_edit":
        admin_card_state[user_id] = {"step": "card_number"}
        await callback.message.answer("شماره کارت جدید را ارسال کنید:", parse_mode="HTML")

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
            # Get all active tutorials
            tutorials = db.query(ServiceTutorial).filter(ServiceTutorial.is_active == True).all()

            if not tutorials:
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                await callback.message.answer(
                    "📚 آموزش\n\nآموزشی یافت نشد.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="back_to_main")]
                    ]),
                    parse_mode="HTML"
                )
                return

            # Send each tutorial
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

            for i, tutorial in enumerate(tutorials):
                service_type = db.query(ServiceType).filter(ServiceType.id == tutorial.service_type_id).first()
                service_name = service_type.name if service_type else ""

                # Send tutorial with media if available
                if tutorial.media_file_id:
                    if tutorial.media_type == "photo":
                        await callback.message.answer_photo(
                            photo=tutorial.media_file_id,
                            caption=f"📚 {tutorial.title}\n\n{service_name}\n\n{tutorial.description or ''}",
                            parse_mode="HTML"
                        )
                    elif tutorial.media_type == "video":
                        await callback.message.answer_video(
                            video=tutorial.media_file_id,
                            caption=f"📚 {tutorial.title}\n\n{service_name}\n\n{tutorial.description or ''}",
                            parse_mode="HTML"
                        )
                else:
                    # No media, just send text
                    await callback.message.answer(
                        f"📚 {tutorial.title}\n\n{service_name}\n\n{tutorial.description or 'بدون توضیحات'}",
                        parse_mode="HTML"
                    )

            # Send back button after all tutorials
            await callback.message.answer(
                "برای بازگشت به منوی اصلی از دکمه زیر استفاده کنید:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="back_to_main")]
                ]),
                parse_mode="HTML"
            )
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
                        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="back_to_main")]
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
                        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="back_to_main")]
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
                await callback.message.answer(
                    "🧪 مدیریت اکانت تست\n\nروی هر پارامتر بزنید تا مقدار جدید را وارد کنید.",
                    reply_markup=get_test_account_keyboard(
                        days_text=str(test_plan.duration_days),
                        traffic_text=format_gb_value(test_plan.traffic_gb),
                        is_active=bool(test_plan.is_active),
                        has_plan=True,
                    ),
                    parse_mode="HTML",
                )
            else:
                await callback.message.answer(
                    "🧪 اکانت تست هنوز تعریف نشده است.",
                    reply_markup=get_test_account_keyboard(has_plan=False),
                    parse_mode="HTML",
                )
        finally:
            db.close()

    elif data == "test_account_ro":
        await callback.answer("این گزینه فقط جهت نمایش است.", show_alert=False)

    elif data == "plan_test_account_edit":
        admin_plan_state[user_id] = {"action": "test_account_setup", "step": "days"}
        await callback.message.answer("⏰ تعداد روز اکانت تست را وارد کنید:", parse_mode="HTML")

    elif data == "plan_test_set_days":
        admin_plan_state[user_id] = {"action": "test_account_setup", "field": "days"}
        await callback.message.answer("⏰ مقدار جدید مدت اکانت تست (روز) را وارد کنید:", parse_mode="HTML")

    elif data == "plan_test_set_traffic":
        admin_plan_state[user_id] = {"action": "test_account_setup", "field": "traffic"}
        await callback.message.answer("🌐 مقدار جدید ترافیک اکانت تست (گیگ) را وارد کنید:\nمثال: <code>1</code> یا <code>0.5</code>", parse_mode="HTML")

    elif data == "plan_test_toggle":
        db = SessionLocal()
        try:
            test_plan = db.query(Plan).filter(Plan.name == TEST_ACCOUNT_PLAN_NAME).first()
            if not test_plan:
                await callback.answer("اکانت تست هنوز ایجاد نشده است.", show_alert=True)
                return
            test_plan.is_active = not bool(test_plan.is_active)
            db.commit()
            await callback.answer("وضعیت اکانت تست تغییر کرد.", show_alert=False)
            await callback.message.answer(
                "🧪 مدیریت اکانت تست\n\nروی هر پارامتر بزنید تا مقدار جدید را وارد کنید.",
                reply_markup=get_test_account_keyboard(
                    days_text=str(test_plan.duration_days),
                    traffic_text=format_gb_value(test_plan.traffic_gb),
                    is_active=bool(test_plan.is_active),
                    has_plan=True,
                ),
                parse_mode="HTML",
            )
        finally:
            db.close()

    elif data == "plan_create":
        admin_plan_state[user_id] = {"action": "create", "plan_id": "new", "step": "name", "data": {}}
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        await callback.message.answer(
            "➕ ایجاد پلن جدید\n\nیک نام برای پلن خود انتخاب کنید.",
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
                selected_server_ids = [m.server_id for m in db.query(PlanServerMap).filter(PlanServerMap.plan_id == plan.id).all()]
                admin_plan_state[user_id] = {
                    "action": "edit",
                    "plan_id": plan_id,
                    "data": {
                        "name": plan.name,
                        "days": str(plan.duration_days),
                        "traffic": str(plan.traffic_gb),
                        "price": str(plan.price),
                        "description": plan.description or "",
                        "service_type_id": plan.service_type_id,
                        "server_ids": selected_server_ids,
                    },
                }
                await callback.message.answer(
                    "📦 مدیریت پلن\n\nروی هر پارامتر بزنید تا در صورت نیاز مقدار جدید وارد کنید.",
                    reply_markup=get_plan_action_keyboard(
                        plan_id=plan.id,
                        plan_name=plan.name,
                        days_text=str(plan.duration_days),
                        traffic_text=format_gb_value(plan.traffic_gb),
                        price_text=f"{plan.price:,}",
                        description_text=(plan.description or "ندارد")[:40],
                        is_active=bool(plan.is_active),
                    ),
                    parse_mode="HTML",
                )
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
                await callback.message.answer(
                    "📦 مدیریت پلن\n\nروی هر پارامتر بزنید تا در صورت نیاز مقدار جدید وارد کنید.",
                    reply_markup=get_plan_action_keyboard(
                        plan_id=plan.id,
                        plan_name=plan.name,
                        days_text=str(plan.duration_days),
                        traffic_text=format_gb_value(plan.traffic_gb),
                        price_text=f"{plan.price:,}",
                        description_text=(plan.description or "ندارد")[:40],
                        is_active=bool(plan.is_active),
                    ),
                    parse_mode="HTML",
                )
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
        await callback.message.answer(f"📝 اگر می‌خواهید نام پلن را تغییر دهید، مقدار جدید را وارد کنید:\n\nنام فعلی: <code>{current or '-'}</code>", parse_mode="HTML")

    elif data.startswith("plan_set_days_"):
        plan_id = data.split("_")[-1]
        current_state = admin_plan_state.get(user_id, {})
        current = current_state.get("data", {}).get("days", "")
        admin_plan_state[user_id] = {"action": "create" if plan_id == "new" else "edit", "plan_id": plan_id, "field": "days", "data": current_state.get("data", {})}
        await callback.message.answer(f"⏰ اگر می‌خواهید مدت را تغییر دهید، تعداد روز جدید را وارد کنید:\n\nمقدار فعلی: <code>{current or '-'}</code>", parse_mode="HTML")

    elif data.startswith("plan_set_traffic_"):
        plan_id = data.split("_")[-1]
        current_state = admin_plan_state.get(user_id, {})
        current = current_state.get("data", {}).get("traffic", "")
        admin_plan_state[user_id] = {"action": "create" if plan_id == "new" else "edit", "plan_id": plan_id, "field": "traffic", "data": current_state.get("data", {})}
        await callback.message.answer(f"🌐 اگر می‌خواهید ترافیک را تغییر دهید، مقدار جدید (گیگ) را وارد کنید:\n\nمقدار فعلی: <code>{current or '-'}</code>", parse_mode="HTML")

    elif data.startswith("plan_set_price_"):
        plan_id = data.split("_")[-1]
        current_state = admin_plan_state.get(user_id, {})
        current = current_state.get("data", {}).get("price", "")
        admin_plan_state[user_id] = {"action": "create" if plan_id == "new" else "edit", "plan_id": plan_id, "field": "price", "data": current_state.get("data", {})}
        await callback.message.answer(f"💰 اگر می‌خواهید قیمت را تغییر دهید، قیمت جدید را وارد کنید:\n\nمقدار فعلی: <code>{current or '-'}</code>", parse_mode="HTML")

    elif data.startswith("plan_set_desc_"):
        plan_id = data.split("_")[-1]
        current_state = admin_plan_state.get(user_id, {})
        current = current_state.get("data", {}).get("description", "")
        admin_plan_state[user_id] = {"action": "create" if plan_id == "new" else "edit", "plan_id": plan_id, "field": "description", "data": current_state.get("data", {})}
        await callback.message.answer(f"📄 اگر می‌خواهید توضیحات را تغییر دهید، متن جدید را وارد کنید:\n\nمقدار فعلی: <code>{current or '-'}</code>", parse_mode="HTML")

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
                card_number, card_holder = get_card_info()
                card_text = card_number if card_number else "هنوز شماره کارتی داده نشده"
                holder_text = card_holder if card_holder else "-"
                msg = f"💳 پرداخت کارت به کارت\n\nپلن: {plan.name}\nقیمت نهایی: {final_price} تومان\n\nلطفاً به شماره کارت زیر واریز کنید:\n\n🪪 شماره کارت:\n<code>{card_text}</code>\n\n👤 صاحب حساب: {holder_text}\n\nپس از واریز، تصویر فیش واریزی را ارسال کنید."
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

                if receipt.payment_method == "wallet_topup":
                    wallet_user = get_user(db, receipt.user_telegram_id)
                    if wallet_user:
                        wallet_user.wallet_balance = (wallet_user.wallet_balance or 0) + (receipt.amount or 0)
                        db.commit()
                        try:
                            await callback.message.bot.send_message(
                                chat_id=int(receipt.user_telegram_id),
                                text=f"✅ مبلغ {receipt.amount:,} تومان با اعتبار شما اضافه گردید.",
                                parse_mode="HTML"
                            )
                        except Exception as e:
                            print(f"Error notifying wallet topup approval: {e}")
                    await callback.message.answer(
                        f"✅ شارژ کیف پول تایید شد.\n\n• مبلغ: {receipt.amount:,} تومان\n• کاربر: {receipt.user_telegram_id}",
                        reply_markup=get_receipt_done_keyboard(),
                        parse_mode="HTML"
                    )
                    return True

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

    else:
        return False
    return True
