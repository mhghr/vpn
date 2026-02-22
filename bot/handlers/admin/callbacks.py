from ..common import *
from .servers import handle_server_management_callbacks
from .plans import handle_plan_management_callbacks

async def handle_admin_callbacks(callback: CallbackQuery, bot, data: str, user_id: int) -> bool:
    if data == "admin":
        pending_panel = load_pending_panel()
        await callback.message.answer(ADMIN_MESSAGE, reply_markup=get_admin_keyboard(pending_panel), parse_mode="HTML")

    elif data == "admin_card_settings":
        card_number, card_holder = get_card_info()
        await callback.message.answer("💳 مدیریت اطلاعات کارت", reply_markup=get_admin_card_keyboard(card_number, card_holder), parse_mode="HTML")

    elif data in {"admin_card_ro", "admin_card_edit"}:
        admin_card_state[user_id] = {"step": "card_number"}
        await callback.message.answer("مقدار جدید شماره کارت را وارد کنید:", parse_mode="HTML")

    elif data in {"admin_card_holder_ro", "admin_card_holder_edit"}:
        admin_card_state[user_id] = {"step": "card_holder"}
        await callback.message.answer("مقدار جدید نام صاحب حساب را وارد کنید:", parse_mode="HTML")

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

    elif data == "admin_search":
        admin_user_search_state.pop(user_id, None)
        await callback.message.answer("نوع جستجو را انتخاب کنید:", reply_markup=get_admin_search_keyboard(), parse_mode="HTML")

    elif data == "admin_search_user":
        admin_user_search_state[user_id] = {"active": True, "mode": "user"}
        await callback.message.answer(SEARCH_USER_MESSAGE, parse_mode="HTML")

    elif data == "admin_search_config":
        admin_user_search_state[user_id] = {"active": True, "mode": "config"}
        await callback.message.answer("متن جستجوی کانفیگ را وارد کنید (IP، پلن یا شناسه کاربر):", parse_mode="HTML")

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
            financials = calculate_org_user_financials(db, user_obj)
            await callback.message.answer("💼 مالی مشتری سازمانی:", reply_markup=get_org_finance_keyboard(
                total_traffic_text=f"{financials['total_traffic_gb']:.2f} GB",
                price_per_gb_text=f"{financials['price_per_gb']:,} تومان",
                debt_text=f"{financials['debt_amount']:,} تومان",
                last_settlement_text=financials['last_settlement'],
                owner="admin",
                editable_price=True,
                user_id=user_obj.id,
            ), parse_mode="HTML")
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
            admin_plan_state[user_id] = {"action": "edit_org_price", "target_user_id": user_obj.id}
            await callback.message.answer(f"هزینه فعلی هر گیگ: {(user_obj.org_price_per_gb or 0):,} تومان\nمقدار جدید را وارد کنید:", parse_mode="HTML")
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
            financials = calculate_org_user_financials(db, user_obj)
            await callback.message.answer("💼 مالی مشتری سازمانی:", reply_markup=get_org_finance_keyboard(
                total_traffic_text=f"{financials['total_traffic_gb']:.2f} GB",
                price_per_gb_text=f"{financials['price_per_gb']:,} تومان",
                debt_text=f"{financials['debt_amount']:,} تومان",
                last_settlement_text=financials['last_settlement'],
                owner="admin",
                editable_price=True,
                user_id=user_obj.id,
            ), parse_mode="HTML")
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

            plan = db.query(Plan).filter(Plan.id == config.plan_id).first() if config.plan_id else None
            plan_traffic_bytes, remaining_bytes = get_config_remaining_bytes(config, plan)
            consumed_bytes = get_config_consumed_bytes(config)
            expires_at = get_config_expires_at(config, plan)
            duration_days, traffic_limit_gb = get_config_limits(config, plan)

            now = datetime.utcnow()
            is_expired_by_date = bool(expires_at and expires_at <= now)
            is_expired_by_traffic = bool(plan_traffic_bytes and remaining_bytes <= 0)
            is_disabled = config.status in ["expired", "revoked", "disabled"]
            can_renew = bool(is_expired_by_date or is_expired_by_traffic or is_disabled)

            remaining_days = "نامشخص"
            if expires_at:
                days_left = int((expires_at - now).total_seconds() // 86400)
                remaining_days = str(max(days_left, 0))

            status_text = "🔴 غیرفعال" if config.status != "active" else "🟢 فعال"

            server = db.query(Server).filter(Server.id == config.server_id).first() if config.server_id else None
            details = {
                "user": config.user_telegram_id,
                "plan": config.plan_name or "بدون پلن",
                "server": server.name if server else "-",
                "created": format_jalali_date(config.created_at),
                "renewed": format_jalali_date(config.renewed_at),
                "days": duration_days if duration_days is not None else "نامشخص",
                "traffic": traffic_limit_gb if traffic_limit_gb is not None else "نامشخص",
                "used": format_traffic_size(consumed_bytes),
                "remaining": format_traffic_size(remaining_bytes) if plan_traffic_bytes else "نامحدود/نامشخص",
                "days_left": remaining_days,
                "status": status_text,
            }
            await callback.message.answer("📋 جزئیات کانفیگ:", reply_markup=get_admin_config_detail_keyboard(config.id, details, can_renew=can_renew), parse_mode="HTML")
        finally:
            db.close()

    elif data.startswith("admin_cfg_edit_traffic_"):
        config_id = int(data.replace("admin_cfg_edit_traffic_", ""))
        db = SessionLocal()
        try:
            cfg = db.query(WireGuardConfig).filter(WireGuardConfig.id == config_id).first()
            current = cfg.traffic_limit_gb if cfg else "-"
        finally:
            db.close()
        admin_plan_state[user_id] = {"action": "edit_config", "field": "traffic", "config_id": config_id}
        await callback.message.answer(f"مقدار فعلی ترافیک: {current} گیگ\nمقدار جدید را وارد کنید:", parse_mode="HTML")

    elif data.startswith("admin_cfg_edit_days_"):
        config_id = int(data.replace("admin_cfg_edit_days_", ""))
        db = SessionLocal()
        try:
            cfg = db.query(WireGuardConfig).filter(WireGuardConfig.id == config_id).first()
            current = cfg.duration_days if cfg else "-"
        finally:
            db.close()
        admin_plan_state[user_id] = {"action": "edit_config", "field": "days", "config_id": config_id}
        await callback.message.answer(f"تعداد روز فعلی: {current}\nمقدار جدید را وارد کنید:", parse_mode="HTML")

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
                server = db.query(Server).filter(Server.id == config.server_id, Server.is_active == True).first()
                if server:
                    wireguard.disable_wireguard_peer(
                        mikrotik_host=server.host,
                        mikrotik_user=server.username,
                        mikrotik_pass=server.password,
                        mikrotik_port=server.api_port,
                        wg_interface=server.wg_interface,
                        client_ip=config.client_ip
                    )
            except Exception as e:
                print(f"MikroTik disable error: {e}")

            config.status = "disabled"
            db.commit()
            await callback.message.answer("✅ کانفیگ غیرفعال شد.", parse_mode="HTML")

            # Show config detail again
            details = {"user": config.user_telegram_id, "plan": config.plan_name or "بدون پلن", "server": "-", "created": format_jalali_date(config.created_at), "renewed": format_jalali_date(config.renewed_at), "days": config.duration_days or "نامشخص", "traffic": config.traffic_limit_gb or "نامشخص", "used": format_traffic_size(get_config_consumed_bytes(config)), "remaining": "-", "days_left": "-", "status": "🔴 غیرفعال"}
            await callback.message.answer("📋 جزئیات کانفیگ:", reply_markup=get_admin_config_detail_keyboard(config.id, details, can_renew=True), parse_mode="HTML")
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
                server = db.query(Server).filter(Server.id == config.server_id, Server.is_active == True).first()
                if server:
                    wireguard.delete_wireguard_peer(
                        mikrotik_host=server.host,
                        mikrotik_user=server.username,
                        mikrotik_pass=server.password,
                        mikrotik_port=server.api_port,
                        wg_interface=server.wg_interface,
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

    elif await handle_server_management_callbacks(callback, bot, data, user_id):
        return True

    elif await handle_plan_management_callbacks(callback, bot, data, user_id):
        return True

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
                holder_text = card_holder if card_holder else "نام صاحب حساب"
                msg = (
                    f"💳 پرداخت کارت به کارت\n\n"
                    f"پلن: {plan.name} ( {final_price:,} تومان )\n\n\n"
                    f" لطفاً مبلغ {final_price:,} تومان به شماره کارت زیر واریز کنید و تصویر فیش واریزی رو در همین مرحله آپلود کنید .\n\n"
                    f"<code>{card_text}</code>\n\n"
                    f"{holder_text}"
                )
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

                if receipt.payment_method == "org_settlement":
                    org_user = get_user(db, receipt.user_telegram_id)
                    if org_user:
                        configs = db.query(WireGuardConfig).filter(WireGuardConfig.user_telegram_id == receipt.user_telegram_id, WireGuardConfig.status == "active").all()
                        for cfg in configs:
                            try:
                                server = db.query(Server).filter(Server.id == cfg.server_id).first() if cfg.server_id else None
                                if server:
                                    import wireguard
                                    wireguard.reset_wireguard_peer_traffic(
                                        mikrotik_host=server.host, mikrotik_user=server.username, mikrotik_pass=server.password, mikrotik_port=server.api_port, wg_interface=server.wg_interface, client_ip=cfg.client_ip
                                    )
                            except Exception as e:
                                print(f"Org settle router reset failed: {e}")
                            cfg.cumulative_rx_bytes = 0
                            cfg.cumulative_tx_bytes = 0
                            cfg.last_rx_counter = 0
                            cfg.last_tx_counter = 0
                            cfg.counter_reset_flag = True
                        org_user.org_last_settlement_at = datetime.utcnow()
                        db.commit()
                    await callback.message.answer("✅ تسویه سازمانی تایید شد و شمارنده مصرف ریست شد.", parse_mode="HTML")
                    try:
                        await callback.message.edit_reply_markup(reply_markup=get_receipt_done_keyboard("✅ تایید شد"))
                    except Exception:
                        pass
                    return True

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
                    try:
                        await callback.message.edit_reply_markup(
                            reply_markup=get_receipt_done_keyboard("✅ تایید شد")
                        )
                    except Exception:
                        pass
                    return True

                if receipt.renew_config_id:
                    renew_config = db.query(WireGuardConfig).filter(
                        WireGuardConfig.id == receipt.renew_config_id,
                        WireGuardConfig.user_telegram_id == receipt.user_telegram_id,
                    ).first()
                    plan = db.query(Plan).filter(Plan.id == receipt.plan_id).first() if receipt.plan_id else None
                    if not renew_config or not plan:
                        await callback.message.answer(
                            "❌ کانفیگ/پلن تمدید یافت نشد.",
                            reply_markup=get_receipt_done_keyboard("⚠️ بررسی دستی لازم است"),
                            parse_mode="HTML"
                        )
                        try:
                            await callback.message.edit_reply_markup(
                                reply_markup=get_receipt_done_keyboard("✅ تایید شد")
                            )
                        except Exception:
                            pass
                        return True

                    server = db.query(Server).filter(Server.id == renew_config.server_id).first() if renew_config.server_id else None
                    if not server:
                        server = db.query(Server).filter(Server.id == receipt.server_id).first() if receipt.server_id else None
                    if not server:
                        available = get_available_servers_for_plan(db, plan.id)
                        server = available[0] if available else None

                    reset_ok = False
                    if server:
                        try:
                            import wireguard
                            reset_ok = wireguard.reset_wireguard_peer_traffic(
                                mikrotik_host=server.host,
                                mikrotik_user=server.username,
                                mikrotik_pass=server.password,
                                mikrotik_port=server.api_port,
                                wg_interface=server.wg_interface,
                                client_ip=renew_config.client_ip,
                            )
                        except Exception as e:
                            print(f"Renew reset peer failed: {e}")

                    renew_config.status = "active"
                    renew_config.duration_days = plan.duration_days
                    renew_config.traffic_limit_gb = plan.traffic_gb
                    renew_config.expires_at = datetime.utcnow() + timedelta(days=(plan.duration_days or 0))
                    renew_config.renewed_at = datetime.utcnow()
                    renew_config.cumulative_rx_bytes = 0
                    renew_config.cumulative_tx_bytes = 0
                    renew_config.last_rx_counter = 0
                    renew_config.last_tx_counter = 0
                    renew_config.counter_reset_flag = True
                    renew_config.low_traffic_alert_sent = False
                    renew_config.expiry_alert_sent = False
                    renew_config.threshold_alert_sent = False
                    db.commit()

                    try:
                        await callback.message.bot.send_message(
                            chat_id=int(receipt.user_telegram_id),
                            text=f"✅ سرویس شما با موفقیت تمدید شد.\n\n• پلن: {plan.name}\n• تاریخ انقضای جدید: {format_jalali_date(renew_config.expires_at)}",
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        print(f"Error notifying user for renew approve: {e}")

                    await callback.message.answer(
                        (
                            f"✅ پرداخت تمدید تایید شد.\n\n"
                            f"• کاربر: {receipt.user_telegram_id}\n"
                            f"• کانفیگ: {renew_config.client_ip}\n"
                            f"• پلن: {plan.name}\n"
                            f"• انقضای جدید: {format_jalali_date(renew_config.expires_at)}\n"
                            f"• ریست کانتر روتر: {'✅ انجام شد' if reset_ok else '⚠️ انجام نشد (نیازمند بررسی دستی)'}"
                        ),
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
                                            f"🏷 نام کانفیگ: {wg_result.get('peer_comment', 'نامشخص')}\n"
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
                    try:
                        await callback.message.edit_reply_markup(
                            reply_markup=get_receipt_done_keyboard("✅ تایید شد")
                        )
                    except Exception:
                        pass
                else:
                    await callback.message.answer(
                        f"✅ پرداخت تایید شد!\n\n• پلن: {receipt.plan_name}\n• مبلغ: {receipt.amount} تومان\n• کاربر: {receipt.user_telegram_id}\n\n⚠️ حساب WireGuard ایجاد نشد. لطفاً دستی ایجاد کنید.",
                        reply_markup=get_receipt_done_keyboard(),
                        parse_mode="HTML"
                    )
                    try:
                        await callback.message.edit_reply_markup(
                            reply_markup=get_receipt_done_keyboard("✅ تایید شد")
                        )
                    except Exception:
                        pass
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
        admin_receipt_reject_state[user_id] = {
            "receipt_id": receipt_id,
            "chat_id": callback.message.chat.id,
            "message_id": callback.message.message_id,
        }
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
