import asyncio
import sys
from aiogram import Bot

from database import init_db
from config import TOKEN
from handlers import dp
from services.monitoring_service import (
    usage_sync_worker,
    notify_plan_thresholds_worker,
    cleanup_expired_test_accounts_worker,
)

print("Starting bot...", file=sys.stderr)
print(f"Token loaded: {TOKEN[:10]}...", file=sys.stderr)
print("Initializing database...", file=sys.stderr)
init_db()
print("Database initialized", file=sys.stderr)

bot = Bot(token=TOKEN)
print("Bot instance created", file=sys.stderr)

async def main():
    usage_task = None
    notify_task = None
    test_cleanup_task = None
    try:
        print("Deleting webhook...", file=sys.stderr)
        await bot.delete_webhook(drop_pending_updates=True)
        usage_task = asyncio.create_task(usage_sync_worker())
        notify_task = asyncio.create_task(notify_plan_thresholds_worker(bot))
        test_cleanup_task = asyncio.create_task(cleanup_expired_test_accounts_worker(bot))
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
