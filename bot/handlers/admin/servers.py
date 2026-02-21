from ..common import *

async def handle_server_management_callbacks(callback: CallbackQuery, bot, data: str, user_id: int) -> bool:
    if data == "admin_servers":
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
    else:
        return False
    return True
