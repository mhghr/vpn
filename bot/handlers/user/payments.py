from aiogram.types import Message
from ..common import *

@dp.message(lambda message: message.from_user.id in user_payment_state and user_payment_state.get(message.from_user.id, {}).get("step") == "discount_code")
async def handle_discount_code_input(message: Message):
    user_id = message.from_user.id
    code_text = message.text.strip().upper()
    state = user_payment_state.get(user_id, {})
    plan_id = state.get("plan_id")
    if not plan_id:
        await message.answer("❌ ابتدا پلن را انتخاب کنید.", parse_mode="HTML")
        return

    db = SessionLocal()
    try:
        plan = db.query(Plan).filter(Plan.id == plan_id).first()
        gift = db.query(GiftCode).filter(GiftCode.code == code_text, GiftCode.is_active == True).first()
        if not plan or not gift:
            await message.answer("❌ کد تخفیف نامعتبر است.", parse_mode="HTML")
            return
        if gift.expires_at and gift.expires_at < datetime.utcnow():
            await message.answer("❌ اعتبار این کد تخفیف تمام شده است.", parse_mode="HTML")
            return
        if gift.used_count >= gift.max_uses:
            await message.answer("❌ ظرفیت استفاده این کد تکمیل شده است.", parse_mode="HTML")
            return

        discount_amount = 0
        if gift.discount_percent:
            discount_amount = int((plan.price * gift.discount_percent) / 100)
        elif gift.discount_amount:
            discount_amount = gift.discount_amount

        final_price = max(plan.price - discount_amount, 0)
        state["discount_amount"] = discount_amount
        state["price"] = final_price
        state["gift_code"] = gift.code
        state.pop("step", None)
        user_payment_state[user_id] = state

        renew_config_id = state.get("renew_config_id")
        kb = get_payment_method_keyboard_for_renew(plan.id, renew_config_id) if renew_config_id else get_payment_method_keyboard(plan.id)
        await message.answer(
            f"✅ کد اعمال شد.\nقیمت اصلی: {plan.price} تومان\nمیزان تخفیف: {discount_amount} تومان\nقیمت نهایی: {final_price} تومان",
            reply_markup=kb,
            parse_mode="HTML"
        )
    finally:
        db.close()

# Receipt photo handler
@dp.message(lambda message: message.from_user.id in user_payment_state and user_payment_state.get(message.from_user.id, {}).get("method") == "card_to_card")
async def handle_receipt_photo(message: Message):
    user_id = message.from_user.id
    
    # Check if user is in payment state and expecting a receipt
    if user_id not in user_payment_state:
        return
    
    payment_info = user_payment_state[user_id]
    if payment_info.get("method") != "card_to_card":
        return
    
    # Check if message has a photo
    if not message.photo:
        await message.answer("❌ لطفاً تصویر فیش واریزی را ارسال کنید.", parse_mode="HTML")
        return
    
    # Get the photo file ID
    photo = message.photo[-1]  # Get the highest resolution
    file_id = photo.file_id
    
    # Save receipt to database
    db = SessionLocal()
    try:
        receipt = PaymentReceipt(
            user_telegram_id=str(user_id),
            plan_id=payment_info["plan_id"],
            plan_name=payment_info["plan_name"],
            amount=payment_info["price"],
            payment_method="card_to_card",
            server_id=payment_info.get("server_id"),
            receipt_file_id=file_id,
            status="pending"
        )
        db.add(receipt)

        gift_code = payment_info.get("gift_code")
        if gift_code:
            gift = db.query(GiftCode).filter(GiftCode.code == gift_code).first()
            if gift:
                gift.used_count = (gift.used_count or 0) + 1

        db.commit()
        
        # Clear payment state
        del user_payment_state[user_id]
        
        # Send confirmation to user
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        await message.answer(
            "✅ فیش پرداخت دریافت شد!\n\n⏰ لطفاً منتظر تایید پرداخت توسط مدیریت باشید.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="back_to_main")]
            ]),
            parse_mode="HTML"
        )
        
        # Get user info for admin notification
        user = message.from_user
        user_display_name = f"{user.first_name}"
        if user.last_name:
            user_display_name += f" {user.last_name}"
        user_username = f"@{user.username}" if user.username else "ندارد"
        
        # Forward receipt to admin
        for admin_id in ADMIN_IDS:
            try:
                # Send photo with user info in caption
                caption_text = f"💳 درخواست تایید پرداخت جدید\n\n👤 اطلاعات کاربر:\n• نام: {user_display_name}\n• آیدی: {user_id}\n• نام کاربری: {user_username}\n\n💰 اطلاعات پرداخت:\n• پلن: {payment_info['plan_name']}\n• مبلغ: {payment_info['price']} تومان\n• روش پرداخت: کارت به کارت"
                await message.bot.send_photo(
                    chat_id=admin_id,
                    photo=file_id,
                    caption=caption_text,
                    reply_markup=get_receipt_action_keyboard(receipt.id),
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Error sending to admin: {e}")
                
    except Exception as e:
        await message.answer(f"❌ خطا در ذخیره فیش: {str(e)}", parse_mode="HTML")
    finally:
        db.close()
