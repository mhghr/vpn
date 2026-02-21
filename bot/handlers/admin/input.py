from aiogram.types import Message
from ..common import *

@dp.message(lambda message: is_admin(message.from_user.id))
async def handle_admin_input(message: Message):
    user_id = message.from_user.id
    text = message.text.strip()
    
    if user_id in admin_card_state:
        state = admin_card_state[user_id]
        if state.get("step") == "card_number":
            card_number = normalize_numbers(text).replace(" ", "")
            set_card_info(card_number, "")
            del admin_card_state[user_id]
            await message.answer("✅ شماره کارت با موفقیت ذخیره شد.", parse_mode="HTML")
            await message.answer("💳 مدیریت شماره کارت", reply_markup=get_admin_card_keyboard(card_number), parse_mode="HTML")
            return

    # Handle wallet adjust flow
    if user_id in admin_wallet_adjust_state:
        state = admin_wallet_adjust_state[user_id]
        amount = int(normalize_numbers(text)) if normalize_numbers(text).isdigit() else None
        if amount is None or amount < 0:
            await message.answer("❌ لطفاً عدد معتبر وارد کنید.", parse_mode="HTML")
            return
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == state["target_user_id"]).first()
            if not user:
                await message.answer("❌ کاربر یافت نشد.", parse_mode="HTML")
                return
            if state["op"] == "inc":
                user.wallet_balance += amount
            else:
                user.wallet_balance = max(0, user.wallet_balance - amount)
            db.commit()
            await message.answer(f"✅ موجودی جدید کاربر: {user.wallet_balance} تومان", parse_mode="HTML")
        finally:
            db.close()
            del admin_wallet_adjust_state[user_id]
        return

    # Handle discount create flow
    if user_id in admin_discount_state:
        state = admin_discount_state[user_id]
        step = state.get("step")
        if step == "code":
            state["code"] = text.strip().upper()
            state["step"] = "type"
            await message.answer("نوع تخفیف را وارد کنید: percent یا amount", parse_mode="HTML")
            return
        if step == "type":
            if text.lower() not in ["percent", "amount"]:
                await message.answer("❌ فقط percent یا amount", parse_mode="HTML")
                return
            state["type"] = text.lower()
            state["step"] = "value"
            await message.answer("مقدار تخفیف را وارد کنید.", parse_mode="HTML")
            return
        if step == "value":
            num = int(normalize_numbers(text)) if normalize_numbers(text).isdigit() else None
            if num is None or num <= 0:
                await message.answer("❌ مقدار نامعتبر", parse_mode="HTML")
                return
            state["value"] = num
            state["step"] = "max_uses"
            await message.answer("چند بار قابل استفاده باشد؟", parse_mode="HTML")
            return
        if step == "max_uses":
            num = int(normalize_numbers(text)) if normalize_numbers(text).isdigit() else None
            if num is None or num <= 0:
                await message.answer("❌ مقدار نامعتبر", parse_mode="HTML")
                return
            state["max_uses"] = num
            state["step"] = "valid_days"
            await message.answer("چند روز اعتبار داشته باشد؟", parse_mode="HTML")
            return
        if step == "valid_days":
            num = int(normalize_numbers(text)) if normalize_numbers(text).isdigit() else None
            if num is None or num <= 0:
                await message.answer("❌ مقدار نامعتبر", parse_mode="HTML")
                return
            db = SessionLocal()
            try:
                gift = GiftCode(
                    code=state["code"],
                    discount_percent=state["value"] if state["type"] == "percent" else None,
                    discount_amount=state["value"] if state["type"] == "amount" else None,
                    max_uses=state["max_uses"],
                    expires_at=datetime.utcnow() + timedelta(days=num),
                    is_active=True,
                )
                db.add(gift)
                db.commit()
                await message.answer("✅ کد تخفیف ساخته شد.", parse_mode="HTML")
            finally:
                db.close()
                del admin_discount_state[user_id]
            return

    # Handle receipt reject flow
    if user_id in admin_receipt_reject_state:
        state = admin_receipt_reject_state[user_id]
        receipt_id = state.get("receipt_id")
        reject_reason = text.strip()
        
        db = SessionLocal()
        try:
            receipt = db.query(PaymentReceipt).filter(PaymentReceipt.id == receipt_id).first()
            if receipt:
                receipt.status = "rejected"
                db.commit()
                
                # Notify user about rejection
                try:
                    user_tg_id = int(receipt.user_telegram_id)
                    if receipt.payment_method == "wallet_topup":
                        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                        await message.bot.send_message(
                            chat_id=user_tg_id,
                            text=f"متاسفانه به دلیل؛ {reject_reason} \"افزایش اعتبار انجام نشد.\"",
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="back_to_main")]]),
                            parse_mode="HTML"
                        )
                    else:
                        await message.bot.send_message(
                            chat_id=user_tg_id,
                            text=f"❌ پرداخت شما رد شد.\n\n📋 دلیل: {reject_reason}\n\nبرای اطلاعات بیشتر با پشتیبانی تماس بگیرید.",
                            parse_mode="HTML"
                        )
                except Exception as e:
                    print(f"Error notifying user about rejection: {e}")
                
                await message.answer(f"✅ فیش رد شد و کاربر اطلاع داده شد.\n📋 دلیل: {reject_reason}", reply_markup=get_receipt_done_keyboard(), parse_mode="HTML")
            else:
                await message.answer("❌ فیش پرداخت یافت نشد.", parse_mode="HTML")
        except Exception as e:
            await message.answer(f"❌ خطا: {str(e)}", parse_mode="HTML")
        finally:
            db.close()
            del admin_receipt_reject_state[user_id]
        return
    
    # Handle service type create flow
    if user_id in admin_service_type_state:
        state = admin_service_type_state[user_id]
        if state.get("step") == "name":
            name = text.strip()
            if not name:
                await message.answer("❌ نام نوع سرویس نامعتبر است.", parse_mode="HTML")
                return
            code = slugify_service_code(name)
            db = SessionLocal()
            try:
                exists = db.query(ServiceType).filter(ServiceType.code == code).first()
                if exists:
                    await message.answer("❌ این نوع سرویس قبلاً ثبت شده است.", parse_mode="HTML")
                    return
                row = ServiceType(name=name, code=code, is_active=True)
                db.add(row)
                db.commit()
                await message.answer(f"✅ نوع سرویس {name} اضافه شد.", parse_mode="HTML")
            finally:
                db.close()
                admin_service_type_state.pop(user_id, None)
            return

    # Handle tutorial create flow
    if user_id in admin_tutorial_state:
        state = admin_tutorial_state[user_id]
        step = state.get("step")
        
        # Check for cancel
        if text.strip() == "انصراف" or text.strip() == "cancel":
            del admin_tutorial_state[user_id]
            await message.answer("❌ عملیات لغو شد.", parse_mode="HTML")
            return
        
        if step == "title":
            state["title"] = text.strip()
            state["step"] = "description"
            await message.answer(
                "✅ عنوان ثبت شد.\n\n"
                "حالا لطفاً متن آموزش را وارد کنید:\n"
                "(می‌تواند خالی باشد)",
                parse_mode="HTML"
            )
            return
        
        if step == "description":
            state["description"] = text.strip()
            state["step"] = "media"
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            await message.answer(
                "✅ متن ثبت شد.\n\n"
                "حالا عکس یا ویدیوی آموزش را آپلود کنید:\n"
                "(اگر نمی‌خواهید رسانه‌ای اضافه کنید، دکمه زیر را بزنید)",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⏭️ بدون رسانه", callback_data=f"admin_tutorial_skip_media_{state.get('service_type_id')}")]
                ]),
                parse_mode="HTML"
            )
            return

    # Handle representative create flow
    if user_id in admin_representative_state:
        state = admin_representative_state[user_id]
        step = state.get("step")

        if step == "name":
            state["name"] = text.strip()
            state["step"] = "bot_token"
            await message.answer("توکن ربات نمایندگی را وارد کنید:", parse_mode="HTML")
            return

        if step == "bot_token":
            if ":" not in text.strip():
                await message.answer("❌ توکن ربات معتبر نیست.", parse_mode="HTML")
                return
            state["bot_token"] = text.strip()
            state["step"] = "admin_id"
            await message.answer("آیدی تلگرام ادمین نمایندگی را وارد کنید:", parse_mode="HTML")
            return

        if step == "admin_id":
            normalized = normalize_numbers(text.strip())
            if not normalized.isdigit():
                await message.answer("❌ آیدی ادمین باید عددی باشد.", parse_mode="HTML")
                return
            state["admin_telegram_id"] = normalized
            state["step"] = "channel_id"
            await message.answer("آیدی یا یوزرنیم کانال نمایندگی را وارد کنید (مثل @mychannel یا -100...):", parse_mode="HTML")
            return

        if step == "channel_id":
            channel_id = text.strip().replace(" ", "")
            if not channel_id:
                await message.answer("❌ آیدی کانال نامعتبر است.", parse_mode="HTML")
                return

            db = SessionLocal()
            try:
                rep = Representative(
                    name=state.get("name") or "نمایندگی",
                    bot_token=state.get("bot_token"),
                    admin_telegram_id=state.get("admin_telegram_id"),
                    channel_id=channel_id,
                    is_active=True,
                )
                db.add(rep)
                db.commit()
                db.refresh(rep)

                ok, output = start_representative_container(rep)
                rep.is_active = ok
                db.commit()

                status = "✅ نمایندگی ساخته شد و کانتینر اجرا شد." if ok else "⚠️ نمایندگی ثبت شد اما اجرای کانتینر ناموفق بود."
                await message.answer(
                    f"{status}\n\n"
                    f"• نام: {rep.name}\n"
                    f"• کانال: {rep.channel_id}\n"
                    f"• کانتینر: {rep.docker_container_name or '-'}\n"
                    f"• نتیجه: {output[:500]}",
                    parse_mode="HTML"
                )
            finally:
                db.close()
                admin_representative_state.pop(user_id, None)
            return

    # Handle server create/edit flow
    if user_id in admin_server_state:
        state = admin_server_state[user_id]
        
        # Check for cancel
        if text.strip() == "انصراف" or text.strip() == "cancel":
            del admin_server_state[user_id]
            await message.answer("❌ عملیات لغو شد.", parse_mode="HTML")
            return
        
        if state.get("step") == "edit_capacity":
            db = SessionLocal()
            try:
                srv = db.query(Server).filter(Server.id == state.get("server_id")).first()
                if not srv:
                    await message.answer("❌ سرور یافت نشد.", parse_mode="HTML")
                    return
                srv.capacity = int(normalize_numbers(text) or 0)
                db.commit()
                await message.answer("✅ ظرفیت سرور ویرایش شد.", parse_mode="HTML")
            finally:
                db.close()
                admin_server_state.pop(user_id, None)
            return

        steps = get_server_creation_steps()
        current = state.get("step")
        if current in steps:
            # Validate IP range input
            if current == "wg_client_network_base":
                parsed = parse_ip_range(text.strip())
                if not parsed:
                    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                    await message.answer(
                        "❌ فرمت رنج IP نامعتبر است.\n• CIDR: 192.168.30.0/24\n• رنج: 192.168.30.10-192.168.30.220",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="❌ انصراف", callback_data="server_add_cancel")]
                        ]),
                        parse_mode="HTML"
                    )
                    return
                # Store the parsed info
                state["wg_client_network_base"] = parsed["base_ip"]
                state["wg_ip_range_start"] = parsed.get("start_last", 1)
                state["wg_ip_range_end"] = parsed.get("end_last", 254)
                state["wg_is_ip_range"] = parsed.get("is_range", False)
            else:
                state[current] = text.strip()
            idx = steps.index(current)
            if idx < len(steps) - 1:
                state["step"] = steps[idx + 1]
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                msg, _ = get_server_field_prompt(steps[idx + 1])
                await message.answer(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="❌ انصراف", callback_data="server_add_cancel")]
                ]), parse_mode="HTML")
                return

            db = SessionLocal()
            try:
                srv = Server(
                    name=state.get("name"),
                    service_type_id=state.get("service_type_id"),
                    host=state.get("host"),
                    api_port=int(normalize_numbers(state.get("api_port", "8728")) or 8728),
                    username=state.get("username"),
                    password=state.get("password"),
                    wg_interface=state.get("wg_interface"),
                    wg_server_public_key=state.get("wg_server_public_key"),
                    wg_server_endpoint=state.get("wg_server_endpoint"),
                    wg_server_port=int(normalize_numbers(state.get("wg_server_port", "51820")) or 51820),
                    wg_client_network_base=state.get("wg_client_network_base"),
                    wg_ip_range_start=state.get("wg_ip_range_start"),
                    wg_ip_range_end=state.get("wg_ip_range_end"),
                    wg_is_ip_range=state.get("wg_is_ip_range", False),
                    wg_client_dns=state.get("wg_client_dns"),
                    capacity=int(normalize_numbers(state.get("capacity", "100")) or 100),
                    is_active=True,
                )
                db.add(srv)
                db.commit()
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                await message.answer(
                    f"✅ سرور {srv.name} ثبت شد.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_servers")],
                        [InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="back_to_main")]
                    ]),
                    parse_mode="HTML"
                )
            except Exception as e:
                await message.answer(f"❌ خطا در ثبت سرور: {e}", parse_mode="HTML")
            finally:
                db.close()
                admin_server_state.pop(user_id, None)
            return

    # Handle custom account creation flow
    if user_id in admin_create_account_state:
        state = admin_create_account_state[user_id]
        step = state.get("step")
        
        if step == "name":
            # Validate name input
            account_name = text.strip()
            if not account_name:
                await message.answer("❌ لطفاً نام معتبر وارد کنید.", parse_mode="HTML")
                return
            state["name"] = account_name
            state["step"] = "days"
            await message.answer(f"✅ نام اکانت: {account_name}\n\nحالا لطفاً تعداد روز را وارد کنید:\n(عدد صحیح)", parse_mode="HTML")
            return
        
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
                account_name = state.get("name", "")
                
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
                        user_telegram_id=str(user_id),
                        plan_id=None,
                        plan_name=account_name,
                        duration_days=days
                    )
                    
                    if wg_result.get("success"):
                        client_ip = wg_result.get("client_ip", "N/A")
                        config = wg_result.get("config", "")
                        
                        # Send summary + config file + QR to admin
                        await message.answer(
                            f"✅ اکانت وایرگارد دلخواه ایجاد شد!\n\n📋 اطلاعات اکانت:\n• مدت: {days} روز\n• حجم: {traffic} گیگ\n• آی پی: {client_ip}",
                            parse_mode="HTML"
                        )
                        
                        # Send config file
                        if config:
                            await send_wireguard_config_file(
                                message,
                                config,
                                caption="📄 فایل کانفیگ WireGuard"
                            )
                        
                        # Send QR if available
                        if wg_result.get("qr_code"):
                            await send_qr_code(
                                message,
                                wg_result.get("qr_code"),
                                f"QR Code - {days}روز / {traffic}گیگ"
                            )
                            await message.answer(
                                f"🏷 نام کانفیگ: <code>{wg_result.get('peer_comment', 'نامشخص')}</code>\n"
                                f"📦 پلن انتخابی: {account_name}",
                                parse_mode="HTML"
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

        if state.get("action") == "test_account_setup":
            step = state.get("step")
            field = state.get("field")

            if step == "days":
                try:
                    days = int(parse_positive_number(text, allow_float=False))
                except ValueError:
                    await message.answer("❌ لطفاً تعداد روز را به‌صورت عدد صحیح بزرگ‌تر از صفر وارد کنید.", parse_mode="HTML")
                    return
                admin_plan_state[user_id] = {"action": "test_account_setup", "step": "traffic", "days": days}
                await message.answer("🌐 حجم اکانت تست را به گیگ وارد کنید (مثلاً <code>1</code> یا <code>0.5</code>):", parse_mode="HTML")
                return

            if step == "traffic":
                try:
                    traffic = float(parse_positive_number(text, allow_float=True))
                except ValueError:
                    await message.answer("❌ لطفاً حجم را به‌صورت عدد بزرگ‌تر از صفر وارد کنید.", parse_mode="HTML")
                    return

                days = state.get("days", 1)
                db = SessionLocal()
                try:
                    test_plan = db.query(Plan).filter(Plan.name == TEST_ACCOUNT_PLAN_NAME).first()
                    if test_plan:
                        test_plan.duration_days = days
                        test_plan.traffic_gb = traffic
                        test_plan.price = 0
                        test_plan.is_active = True
                        test_plan.description = "پلن تست یک‌بار مصرف"
                        action_text = "به‌روزرسانی شد"
                    else:
                        test_plan = Plan(
                            name=TEST_ACCOUNT_PLAN_NAME,
                            duration_days=days,
                            traffic_gb=traffic,
                            price=0,
                            is_active=True,
                            description="پلن تست یک‌بار مصرف",
                        )
                        db.add(test_plan)
                        action_text = "ایجاد شد"
                    db.commit()
                    await message.answer(f"✅ اکانت تست با موفقیت {action_text}.", parse_mode="HTML")
                    await message.answer(
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
                    admin_plan_state.pop(user_id, None)
                return

            if field in {"days", "traffic"}:
                try:
                    value = parse_positive_number(text, allow_float=(field == "traffic"))
                except ValueError:
                    if field == "traffic":
                        await message.answer("❌ لطفاً ترافیک را به‌صورت عدد بزرگ‌تر از صفر وارد کنید.", parse_mode="HTML")
                    else:
                        await message.answer("❌ لطفاً تعداد روز را به‌صورت عدد صحیح بزرگ‌تر از صفر وارد کنید.", parse_mode="HTML")
                    return

                db = SessionLocal()
                try:
                    test_plan = db.query(Plan).filter(Plan.name == TEST_ACCOUNT_PLAN_NAME).first()
                    if not test_plan:
                        await message.answer("❌ اکانت تست هنوز ایجاد نشده است. ابتدا «ایجاد اکانت تست» را بزنید.", parse_mode="HTML")
                        return
                    if field == "days":
                        test_plan.duration_days = int(value)
                    else:
                        test_plan.traffic_gb = float(value)
                    test_plan.price = 0
                    test_plan.description = "پلن تست یک‌بار مصرف"
                    db.commit()
                    await message.answer("✅ مقدار جدید ذخیره شد.", parse_mode="HTML")
                    await message.answer(
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
                    admin_plan_state.pop(user_id, None)
                return


        step = state.get("step")
        field = state.get("field")

        if step:
            if step in ["days", "traffic", "price"]:
                text = normalize_numbers(text)
                try:
                    int(text)
                except ValueError:
                    await message.answer("❌ لطفاً یک عدد صحیح وارد کنید.", parse_mode="HTML")
                    return

            state.setdefault("data", {})[step] = text

            next_steps = {
                "name": "days",
                "days": "traffic",
                "traffic": "price",
            }

            next_step = next_steps.get(step)
            if next_step:
                state["step"] = next_step
                await message.answer(get_plan_field_prompt(next_step), parse_mode="HTML")
            else:
                state.pop("step", None)
                if state.get("action") == "create" and state.get("plan_id") == "new":
                    db = SessionLocal()
                    try:
                        plan_data = state.get("data", {})
                        plan = Plan(
                            name=plan_data["name"],
                            duration_days=int(plan_data["days"]),
                            traffic_gb=int(plan_data["traffic"]),
                            price=int(plan_data["price"]),
                            description=plan_data.get("description", "")
                        )
                        db.add(plan)
                        db.commit()

                        await message.answer(
                            f"✅ پلن «{plan.name}» با موفقیت ایجاد شد.\n\n" + get_plan_creation_summary(state["data"]),
                            parse_mode="HTML"
                        )
                        all_plans = db.query(Plan).all()
                        await message.answer(PLANS_MESSAGE, reply_markup=get_plans_keyboard(all_plans), parse_mode="HTML")
                    finally:
                        db.close()
                        admin_plan_state.pop(user_id, None)
                else:
                    await message.answer(
                        get_plan_creation_summary(state["data"]),
                        reply_markup=get_plan_edit_keyboard(plan_id=None),
                        parse_mode="HTML"
                    )
            return
        
        if field:
            if field in ["days", "traffic", "price"]:
                text = normalize_numbers(text)
                try:
                    int(text)
                except ValueError:
                    await message.answer("❌ لطفاً یک عدد صحیح وارد کنید.", parse_mode="HTML")
                    return
            state.setdefault("data", {})[field] = text
            plan_id = state.get("plan_id", "new")
            action = "ویرایش" if state.get("action") == "edit" else "ایجاد"
            if plan_id == "new":
                await message.answer(f"➕ {action} پلن جدید\n\nاطلاعات وارد شده:\n• نام: {state['data'].get('name', '➖')}\n• مدت: {state['data'].get('days', '➖')} روز\n• ترافیک: {state['data'].get('traffic', '➖')} گیگ\n• قیمت: {state['data'].get('price', '➖')} تومان\n• توضیحات: {state['data'].get('description', '➖')}", reply_markup=get_plan_edit_keyboard(plan_id=None), parse_mode="HTML")
            else:
                await message.answer(f"✏️ {action} پلن\n\nاطلاعات وارد شده:\n• نام: {state['data'].get('name', '➖')}\n• مدت: {state['data'].get('days', '➖')} روز\n• ترافیک: {state['data'].get('traffic', '➖')} گیگ\n• قیمت: {state['data'].get('price', '➖')} تومان\n• توضیحات: {state['data'].get('description', '➖')}", reply_markup=get_plan_edit_keyboard(plan_id=int(plan_id)), parse_mode="HTML")
            return

        await message.answer("❌ لطفاً از دکمه‌های مدیریت پلن استفاده کنید.", parse_mode="HTML")
        return
    
    admin_menu_map = {
        "⚙️ مدیریت": "main_admin",
        "🖥️ پنل‌ها": "admin_panels",
        "🔍 جستجو": "admin_search_user",
        "📦 پلن ها": "admin_plans",
        "💳 فیش‌های پرداخت": "admin_receipts",
        "🎁 کد تخفیف": "admin_discount_create",
        "🧩 انواع سرویس": "admin_service_types",
        "🖧 مدیریت سرورها": "admin_servers",
        "🔗 ساخت اکانت": "admin_create_account",
        "🤝 نمایندگی‌ها": "admin_representatives",
        "📚 آموزش ادمین": "admin_tutorials",
        "🔔 درخواست پنل جدید": "admin_pending_panel",
        "🔙 بازگشت": "back_to_main",
    }
    if text in admin_menu_map:
        action = admin_menu_map[text]
        if action == "main_admin":
            pending_panel = load_pending_panel()
            await message.answer(ADMIN_MESSAGE, reply_markup=get_admin_keyboard(pending_panel), parse_mode="HTML")
            return
        if action == "admin_search_user":
            admin_user_search_state[user_id] = {"active": True}
            await message.answer(SEARCH_USER_MESSAGE, parse_mode="HTML")
            return
        await message.answer("از دکمه‌های داخل صفحه استفاده کنید:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="▶️ باز کردن بخش", callback_data=action)]]), parse_mode="HTML")
        return

    if user_id in admin_user_search_state:
        query = normalize_numbers(text.strip())
        db = SessionLocal()
        try:
            users = search_users(db, query)
            if users:
                await message.answer("نتایج جستجو:", reply_markup=get_found_users_keyboard(users), parse_mode="HTML")
            else:
                await message.answer("❌ کاربری یافت نشد.", parse_mode="HTML")
        finally:
            db.close()
            del admin_user_search_state[user_id]
        return

    db = SessionLocal()
    try:
        user = get_user(db, text) or db.query(User).filter(User.username == text).first()
        if user:
            joined_date = format_jalali_date(user.joined_at) if user.joined_at else "نامشخص"
            msg = f"👤 اطلاعات کاربر:\n\nشناسه: {user.telegram_id}\nنام: {user.first_name}\nنام کاربری: @{user.username}\nموجودی: {user.wallet_balance} تومان\nتاریخ عضویت: {joined_date}\nوضعیت: {'✅ فعال' if user.is_member else '❌ غیرفعال'}\nادمین: {'✅ بله' if user.is_admin else '❌ خیر'}"
            await message.answer(msg, parse_mode="HTML")
        else:
            await message.answer("❌ کاربر یافت نشد.", parse_mode="HTML")
    finally:
        db.close()


