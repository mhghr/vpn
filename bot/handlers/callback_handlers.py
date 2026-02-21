from .common import *
from .user.callbacks import handle_user_callbacks
from .admin.callbacks import handle_admin_callbacks

@dp.callback_query()
async def callback_handler(callback: CallbackQuery, bot):
    data = callback.data
    user_id = callback.from_user.id

    if data.startswith(("admin_", "panel_", "plan_", "rep_")) or data == "admin":
        if not is_admin(user_id):
            await callback.answer("❌ شما دسترسی مدیریت ندارید.", show_alert=True)
            return

    if not is_admin(user_id):
        db_guard = SessionLocal()
        try:
            current_user = get_user(db_guard, str(user_id))
            if current_user and current_user.is_blocked:
                await callback.answer("⛔ حساب شما مسدود است.", show_alert=True)
                return
        finally:
            db_guard.close()

    handled = await handle_user_callbacks(callback, bot, data, user_id)
    if not handled:
        handled = await handle_admin_callbacks(callback, bot, data, user_id)

    if not handled:
        await callback.answer("دستور نامعتبر است.", show_alert=False)
        return

    await callback.answer()
