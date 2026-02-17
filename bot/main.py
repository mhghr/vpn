import asyncio
import sys
from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramBadRequest

# Add debug output
print("Starting bot...", file=sys.stderr)

# Import database and initialize tables
from database import init_db
from config import TOKEN
from handlers import dp

print(f"Token loaded: {TOKEN[:10]}...", file=sys.stderr)

# Initialize database tables
print("Initializing database...", file=sys.stderr)
init_db()
print("Database initialized", file=sys.stderr)

bot = Bot(token=TOKEN)
print("Bot instance created", file=sys.stderr)


async def main():
    try:
        print("Deleting webhook...", file=sys.stderr)
        await bot.delete_webhook(drop_pending_updates=True)
        print("Starting polling...", file=sys.stderr)
        await dp.start_polling(bot)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped", file=sys.stderr)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
