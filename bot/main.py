import asyncio
import sys
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from database import SessionLocal, init_db
from config import TOKEN, MIKROTIK_HOST, MIKROTIK_USER, MIKROTIK_PASS, MIKROTIK_PORT, WG_INTERFACE
from handlers import dp
from wireguard import sync_wireguard_usage_counters, disable_expired_or_exhausted_configs, delete_wireguard_peer
from models import WireGuardConfig, Plan

print("Starting bot...", file=sys.stderr)
print(f"Token loaded: {TOKEN[:10]}...", file=sys.stderr)
print("Initializing database...", file=sys.stderr)
init_db()
print("Database initialized", file=sys.stderr)

bot = Bot(token=TOKEN)
print("Bot instance created", file=sys.stderr)

ONE_GB_IN_BYTES = 1 * (1024 ** 3)
TEST_ACCOUNT_PLAN_NAME = "اکانت تست"


async def notify_plan_thresholds_worker():
    while True:
        db = SessionLocal()
        try:
            now = datetime.now()
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

                if not config.threshold_alert_sent and remaining_bytes <= ONE_GB_IN_BYTES:
                    try:
                        await bot.send_message(
                            chat_id=int(config.user_telegram_id),
                            text=(
                                "⚠️ ترافیک سرویس شما رو به اتمام است.\n"
                                "کمتر از ۱ گیگابایت از حجم پلن شما باقی مانده است.\n"
                                "لطفاً برای تمدید یا خرید پلن جدید اقدام کنید."
                            )
                        )
                        config.low_traffic_alert_sent = True
                        config.expiry_alert_sent = True
                        config.threshold_alert_sent = True
                    except Exception as e:
                        print(f"Low traffic notify failed for {config.user_telegram_id}: {e}", file=sys.stderr)

                days_left = (expires_at - now).total_seconds() / 86400
                if not config.threshold_alert_sent and 0 <= days_left <= 1:
                    try:
                        await bot.send_message(
                            chat_id=int(config.user_telegram_id),
                            text=(
                                "⏳ پلن شما رو به اتمام است.\n"
                                "کمتر از ۱ روز تا پایان اعتبار سرویس شما باقی مانده است.\n"
                                "لطفاً برای تمدید سرویس اقدام کنید."
                            )
                        )
                        config.low_traffic_alert_sent = True
                        config.expiry_alert_sent = True
                        config.threshold_alert_sent = True
                    except Exception as e:
                        print(f"Expiry notify failed for {config.user_telegram_id}: {e}", file=sys.stderr)

            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Threshold notify worker error: {e}", file=sys.stderr)
        finally:
            db.close()

        await asyncio.sleep(180)


async def cleanup_expired_test_accounts_worker():
    while True:
        db = SessionLocal()
        try:
            now = datetime.now()
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
                is_expired = bool(expires_at and expires_at <= now)
                is_exhausted = bool(traffic_limit_bytes and consumed_bytes >= traffic_limit_bytes)

                if not (is_expired or is_exhausted):
                    continue

                try:
                    delete_wireguard_peer(
                        mikrotik_host=MIKROTIK_HOST,
                        mikrotik_user=MIKROTIK_USER,
                        mikrotik_pass=MIKROTIK_PASS,
                        mikrotik_port=MIKROTIK_PORT,
                        wg_interface=WG_INTERFACE,
                        client_ip=config.client_ip,
                    )
                except Exception as e:
                    print(f"Test account peer delete failed ({config.client_ip}): {e}", file=sys.stderr)

                user_tg_id = config.user_telegram_id
                db.delete(config)
                db.commit()

                try:
                    await bot.send_message(chat_id=int(user_tg_id), text="⛔ مهلت تست تمام شده است.")
                except TelegramBadRequest as e:
                    print(f"Test account notify failed for {user_tg_id}: {e}", file=sys.stderr)
                except Exception as e:
                    print(f"Unexpected notify error for {user_tg_id}: {e}", file=sys.stderr)

        except Exception as e:
            db.rollback()
            print(f"Test account cleanup worker error: {e}", file=sys.stderr)
        finally:
            db.close()

        await asyncio.sleep(180)


async def usage_sync_worker():
    while True:
        try:
            sync_wireguard_usage_counters(
                mikrotik_host=MIKROTIK_HOST,
                mikrotik_user=MIKROTIK_USER,
                mikrotik_pass=MIKROTIK_PASS,
                mikrotik_port=MIKROTIK_PORT,
                wg_interface=WG_INTERFACE,
            )
            disable_expired_or_exhausted_configs(
                mikrotik_host=MIKROTIK_HOST,
                mikrotik_user=MIKROTIK_USER,
                mikrotik_pass=MIKROTIK_PASS,
                mikrotik_port=MIKROTIK_PORT,
                wg_interface=WG_INTERFACE,
            )
        except Exception as e:
            print(f"Usage sync worker error: {e}", file=sys.stderr)
        await asyncio.sleep(180)


async def main():
    usage_task = None
    notify_task = None
    test_cleanup_task = None
    try:
        print("Deleting webhook...", file=sys.stderr)
        await bot.delete_webhook(drop_pending_updates=True)
        usage_task = asyncio.create_task(usage_sync_worker())
        notify_task = asyncio.create_task(notify_plan_thresholds_worker())
        test_cleanup_task = asyncio.create_task(cleanup_expired_test_accounts_worker())
        print("Starting polling...", file=sys.stderr)
        await dp.start_polling(bot)
    finally:
        if usage_task:
            usage_task.cancel()
        if notify_task:
            notify_task.cancel()
        if test_cleanup_task:
            test_cleanup_task.cancel()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped", file=sys.stderr)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
