import asyncio
import sys
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramBadRequest

# Add debug output
print("Starting bot...", file=sys.stderr)

# Import database and initialize tables
from database import init_db
from database import SessionLocal
from config import TOKEN, MIKROTIK_HOST, MIKROTIK_USER, MIKROTIK_PASS, MIKROTIK_PORT, WG_INTERFACE
from handlers import dp
from wireguard import sync_wireguard_usage_counters, disable_expired_or_exhausted_configs
from models import WireGuardConfig, Plan

print(f"Token loaded: {TOKEN[:10]}...", file=sys.stderr)

# Initialize database tables
print("Initializing database...", file=sys.stderr)
init_db()
print("Database initialized", file=sys.stderr)

bot = Bot(token=TOKEN)
print("Bot instance created", file=sys.stderr)

THREE_GB_IN_BYTES = 3 * (1024 ** 3)


async def notify_plan_thresholds_worker():
    """Notify users when traffic or expiry is close to ending."""
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

                # Ensure expiry exists for old records
                expires_at = config.expires_at or (config.created_at + timedelta(days=plan.duration_days))

                # Remaining traffic in bytes
                plan_traffic_bytes = plan.traffic_gb * (1024 ** 3)
                consumed_bytes = (config.cumulative_rx_bytes or 0) + (config.cumulative_tx_bytes or 0)
                remaining_bytes = max(plan_traffic_bytes - consumed_bytes, 0)

                # Notify for low traffic once
                if not config.low_traffic_alert_sent and remaining_bytes <= THREE_GB_IN_BYTES:
                    try:
                        await bot.send_message(
                            chat_id=int(config.user_telegram_id),
                            text=(
                                "⚠️ ترافیک سرویس شما رو به اتمام است.\n"
                                "کمتر از ۳ گیگابایت از حجم پلن شما باقی مانده است.\n"
                                "لطفاً برای تمدید یا خرید پلن جدید اقدام کنید."
                            )
                        )
                        config.low_traffic_alert_sent = True
                    except Exception as e:
                        print(f"Low traffic notify failed for {config.user_telegram_id}: {e}", file=sys.stderr)

                # Notify for expiry once
                days_left = (expires_at - now).total_seconds() / 86400
                if not config.expiry_alert_sent and 0 <= days_left <= 3:
                    try:
                        await bot.send_message(
                            chat_id=int(config.user_telegram_id),
                            text=(
                                "⏳ پلن شما رو به اتمام است.\n"
                                "کمتر از ۳ روز تا پایان اعتبار سرویس شما باقی مانده است.\n"
                                "لطفاً برای تمدید سرویس اقدام کنید."
                            )
                        )
                        config.expiry_alert_sent = True
                    except Exception as e:
                        print(f"Expiry notify failed for {config.user_telegram_id}: {e}", file=sys.stderr)

            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Threshold notify worker error: {e}", file=sys.stderr)
        finally:
            db.close()

        await asyncio.sleep(1800)


async def usage_sync_worker():
    """Sync wireguard usage counters every 5 minutes."""
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
        await asyncio.sleep(300)


async def main():
    usage_task = None
    notify_task = None
    try:
        print("Deleting webhook...", file=sys.stderr)
        await bot.delete_webhook(drop_pending_updates=True)
        usage_task = asyncio.create_task(usage_sync_worker())
        notify_task = asyncio.create_task(notify_plan_thresholds_worker())
        print("Starting polling...", file=sys.stderr)
        await dp.start_polling(bot)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise
    finally:
        if usage_task:
            usage_task.cancel()
        if notify_task:
            notify_task.cancel()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped", file=sys.stderr)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
