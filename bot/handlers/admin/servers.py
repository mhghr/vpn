from ..common import *


async def handle_server_management_callbacks(callback: CallbackQuery, bot, data: str, user_id: int) -> bool:
    if data == "admin_servers":
        db = SessionLocal()
        try:
            rows = db.query(ServiceType).filter(ServiceType.is_active == True).all()
            await callback.message.answer(
                "🖧 مدیریت سرورها\n\nابتدا نوع سرویس را انتخاب کنید:",
                reply_markup=get_servers_service_type_keyboard(rows),
                parse_mode="HTML"
            )
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
        await callback.message.answer("نام سرور را وارد کنید:", parse_mode="HTML")

    elif data.startswith("server_view_"):
        server_id = int(data.split("_")[-1])
        db = SessionLocal()
        try:
            srv = db.query(Server).filter(Server.id == server_id).first()
            if not srv:
                await callback.message.answer("❌ سرور یافت نشد.", parse_mode="HTML")
                return
            await callback.message.answer(
                "🖧 مدیریت سرور (برای تغییر، روی هر پارامتر بزنید):",
                reply_markup=get_server_detail_keyboard(srv, srv.service_type_id, None),
                parse_mode="HTML"
            )
        finally:
            db.close()

    elif data.startswith("server_field_"):
        parts = data.split("_", 3)
        server_id = int(parts[2])
        field = parts[3]
        prompts = {
            "name": "نام جدید سرور را وارد کنید:",
            "host": "آی‌پی/هاست جدید را وارد کنید:",
            "api_port": "پورت API جدید را وارد کنید:",
            "username": "یوزرنیم جدید را وارد کنید:",
            "password": "پسورد جدید را وارد کنید:",
            "wg_interface": "اینترفیس جدید را وارد کنید:",
            "wg_server_endpoint": "Endpoint جدید را وارد کنید:",
            "wg_server_port": "پورت WireGuard جدید را وارد کنید:",
            "capacity": "ظرفیت جدید را وارد کنید:",
        }
        prompt = prompts.get(field)
        if not prompt:
            await callback.answer("پارامتر نامعتبر", show_alert=True)
            return
        admin_server_state[user_id] = {"step": "edit_field", "server_id": server_id, "field": field}
        await callback.message.answer(prompt, parse_mode="HTML")

    elif data.startswith("server_test_"):
        server_id = int(data.split("_")[-1])
        db = SessionLocal()
        try:
            srv = db.query(Server).filter(Server.id == server_id).first()
            if not srv:
                await callback.message.answer("❌ سرور یافت نشد.", parse_mode="HTML")
                return
            ok, detail = check_server_connection(srv)
            await callback.message.answer(
                "🖧 مدیریت سرور (برای تغییر، روی هر پارامتر بزنید):",
                reply_markup=get_server_detail_keyboard(srv, srv.service_type_id, ok),
                parse_mode="HTML"
            )
            await callback.answer("✅ ارتباط برقرار است" if ok else f"❌ ارتباط برقرار نشد: {detail}", show_alert=not ok)
        finally:
            db.close()

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
