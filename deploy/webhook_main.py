import asyncio
import sys
from datetime import datetime, timedelta

from aiohttp import web
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config import (
    TOKEN,
    WEBHOOK_BASE_URL,
    WEBHOOK_DROP_PENDING_UPDATES,
    WEBHOOK_HOST,
    WEBHOOK_PATH,
    WEBHOOK_PORT,
    WEBHOOK_SECRET_TOKEN,
)
from database import SessionLocal, init_db
from handlers import dp
from models import Plan, Server, ServiceType, WireGuardConfig
from wireguard import (
    delete_wireguard_peer,
    disable_expired_or_exhausted_configs,
    sync_wireguard_usage_counters,
)

print("Starting bot in webhook mode...", file=sys.stderr)
print("Initializing database...", file=sys.stderr)
init_db()

bot = Bot(token=TOKEN)
ONE_GB_IN_BYTES = 1 * (1024 ** 3)
TEST_ACCOUNT_PLAN_NAME = "اکانت تست"
background_tasks = []


def _get_wireguard_servers(db):
    wireguard_type = db.query(ServiceType).filter(ServiceType.code == "wireguard").first()
    if not wireguard_type:
        return []
    return db.query(Server).filter(
        Server.service_type_id == wireguard_type.id,
        Server.is_active == True,
    ).all()


def build_webhook_url() -> str:
    base_url = WEBHOOK_BASE_URL.rstrip("/")
    if not base_url:
        raise ValueError("WEBHOOK_BASE_URL must be set")
    path = WEBHOOK_PATH if WEBHOOK_PATH.startswith("/") else f"/{WEBHOOK_PATH}"
    return f"{base_url}{path}"


async def notify_plan_thresholds_worker():
    while True:
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            configs = db.query(WireGuardConfig).filter(WireGuardConfig.status == "active").all()
            for config in configs:
                if not config.plan_id:
                    continue
                plan = db.query(Plan).filter(Plan.id == config.plan_id).first()
                if not plan or not plan.duration_days or not plan.traffic_gb:
                    continue

                expires_at = config.expires_at or (config.created_at + timedelta(days=plan.duration_days))
                plan_traffic_bytes = plan.traffic_gb * (1024 ** 3)
                consumed_bytes = config.cumulative_rx_bytes or 0
                remaining_bytes = max(plan_traffic_bytes - consumed_bytes, 0)
                days_left = (expires_at - now).total_seconds() / 86400

                if not config.threshold_alert_sent and (remaining_bytes <= ONE_GB_IN_BYTES or 0 <= days_left <= 1):
                    try:
                        await bot.send_message(
                            chat_id=int(config.user_telegram_id),
                            text="⚠️ سرویس شما رو به اتمام است. لطفاً تمدید کنید.",
                        )
                        config.low_traffic_alert_sent = True
                        config.expiry_alert_sent = True
                        config.threshold_alert_sent = True
                    except Exception:
                        pass
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
        await asyncio.sleep(180)


async def cleanup_expired_test_accounts_worker():
    while True:
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            test_plan = db.query(Plan).filter(Plan.name == TEST_ACCOUNT_PLAN_NAME).first()
            if not test_plan:
                await asyncio.sleep(180)
                continue
            configs = db.query(WireGuardConfig).filter(
                WireGuardConfig.status.in_(["active", "expired"]),
                WireGuardConfig.plan_id == test_plan.id,
            ).all()
            for config in configs:
                expires_at = config.expires_at or (config.created_at + timedelta(days=test_plan.duration_days))
                traffic_limit_bytes = (test_plan.traffic_gb or 0) * (1024 ** 3)
                consumed_bytes = config.cumulative_rx_bytes or 0
                if not ((expires_at and expires_at <= now) or (traffic_limit_bytes and consumed_bytes >= traffic_limit_bytes)):
                    continue
                try:
                    server = db.query(Server).filter(Server.id == config.server_id, Server.is_active == True).first()
                    if server:
                        delete_wireguard_peer(
                            mikrotik_host=server.host,
                            mikrotik_user=server.username,
                            mikrotik_pass=server.password,
                            mikrotik_port=server.api_port,
                            wg_interface=server.wg_interface,
                            client_ip=config.client_ip,
                        )
                except Exception:
                    pass
                user_tg_id = config.user_telegram_id
                db.delete(config)
                db.commit()
                try:
                    await bot.send_message(chat_id=int(user_tg_id), text="⛔ مهلت تست تمام شده است.")
                except TelegramBadRequest:
                    pass
        except Exception:
            db.rollback()
        finally:
            db.close()
        await asyncio.sleep(180)


async def usage_sync_worker():
    while True:
        db = SessionLocal()
        try:
            servers = _get_wireguard_servers(db)
            for server in servers:
                sync_wireguard_usage_counters(
                    mikrotik_host=server.host,
                    mikrotik_user=server.username,
                    mikrotik_pass=server.password,
                    mikrotik_port=server.api_port,
                    wg_interface=server.wg_interface,
                )
                disable_expired_or_exhausted_configs(
                    mikrotik_host=server.host,
                    mikrotik_user=server.username,
                    mikrotik_pass=server.password,
                    mikrotik_port=server.api_port,
                    wg_interface=server.wg_interface,
                )
        except Exception:
            pass
        finally:
            db.close()
        await asyncio.sleep(180)


def start_background_workers():
    global background_tasks
    if background_tasks:
        return
    background_tasks = [
        asyncio.create_task(usage_sync_worker()),
        asyncio.create_task(notify_plan_thresholds_worker()),
        asyncio.create_task(cleanup_expired_test_accounts_worker()),
    ]


async def stop_background_workers():
    global background_tasks
    for task in background_tasks:
        task.cancel()
    if background_tasks:
        await asyncio.gather(*background_tasks, return_exceptions=True)
    background_tasks = []


async def on_webhook_startup(app: web.Application):
    start_background_workers()
    await bot.set_webhook(
        url=build_webhook_url(),
        secret_token=WEBHOOK_SECRET_TOKEN or None,
        drop_pending_updates=WEBHOOK_DROP_PENDING_UPDATES,
    )


async def on_webhook_shutdown(app: web.Application):
    await stop_background_workers()
    await bot.session.close()


def run_webhook_mode():
    app = web.Application()
    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET_TOKEN or None,
    ).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    app.on_startup.append(on_webhook_startup)
    app.on_shutdown.append(on_webhook_shutdown)
    web.run_app(app, host=WEBHOOK_HOST, port=WEBHOOK_PORT)


if __name__ == "__main__":
    run_webhook_mode()
