from aiogram.types import Message
from ..common import *

# Admin tutorial media handler (photo/video)
@dp.message(lambda message: message.from_user.id in admin_tutorial_state and admin_tutorial_state.get(message.from_user.id, {}).get("step") == "media")
async def handle_tutorial_media(message: Message):
    user_id = message.from_user.id
    
    if user_id not in admin_tutorial_state:
        return
    
    state = admin_tutorial_state[user_id]
    if state.get("step") != "media":
        return
    
    service_type_id = state.get("service_type_id")
    
    # Check for photo
    if message.photo:
        file_id = message.photo[-1].file_id
        media_type = "photo"
    # Check for video
    elif message.video:
        file_id = message.video.file_id
        media_type = "video"
    else:
        await message.answer("❌ لطفاً عکس یا ویدیو ارسال کنید.", parse_mode="HTML")
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
            existing.media_type = media_type
            existing.media_file_id = file_id
            existing.updated_at = datetime.utcnow()
        else:
            tutorial = ServiceTutorial(
                service_type_id=service_type_id,
                title=state.get("title", ""),
                description=state.get("description", ""),
                media_type=media_type,
                media_file_id=file_id,
                is_active=True
            )
            db.add(tutorial)
        
        db.commit()
        await message.answer(
            f"✅ آموزش ذخیره شد!\nرسانه: {'عکس' if media_type == 'photo' else 'ویدیو'}",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"❌ خطا: {e}", parse_mode="HTML")
    finally:
        db.close()
        del admin_tutorial_state[user_id]

