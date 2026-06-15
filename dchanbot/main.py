"""Main entry point for Dennou-Chan Discord Bot

This script initializes and starts the Discord bot by loading environment
variables and passing configuration paths to the bot instance.
"""

import sys
import logging
import asyncio
import threading
from logging.handlers import RotatingFileHandler

import os
from os.path import join, dirname
from dotenv import load_dotenv
from pathlib import Path

from bot import DChanBot

# Load environment variables defined in a .env file
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(
    dotenv_path = dotenv_path,
    verbose = True
)

def setup_logging():
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        "dchanbot.log",
        maxBytes = 5 * 1024 * 1024,
        backupCount = 5,
        encoding = "utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    logging.basicConfig(
        level = logging.INFO,
        handlers = [console_handler, file_handler],
        force=True,
    )

def console_loop(bot: DChanBot, loop: asyncio.AbstractEventLoop):
    while True:
        try:
            cmd = input("dchanbot > ").strip().lower()
        except EOFError:
            return
        except KeyboardInterrupt:
            return
        
        if cmd in {"shutdown", "quit"}:
            print("Shutdown requested from console.")

            def schedule_shutdown():
                asyncio.create_task(bot.close())

            loop.call_soon_threadsafe(schedule_shutdown)
            return
        
        elif cmd == "help":
            print("Available commands: shutdown, quit, help")

        elif cmd:
            print(f"Unknown command: {cmd}")

async def async_main() -> int:
    """Main function to initialize and start the bot

    Reads configuration and data directory paths from environment variables,
    creates a bot instance, and starts it.

    Returns:
        int: Exit status code.
    """

    setup_logging()

    confroot_str = os.environ.get("DBOT_CONFIG_DIR")
    dataroot_str = os.environ.get("DBOT_DATA_DIR")
    if confroot_str is None:
        raise RuntimeError("DBOT_CONFIG_DIR is not set")
    if dataroot_str is None:
        raise RuntimeError("DBOT_DATA_DIR is not set")

    bot = DChanBot(
        confdir = Path(confroot_str),
        datadir = Path(dataroot_str)
    )

    loop = asyncio.get_running_loop()

    threading.Thread(
        target = console_loop,
        args = (bot, loop),
        daemon = True,
    ).start()

    try:
        await bot.start_async()
    finally:
        if not bot.is_closed():
            await bot.close()

    return 0

def main() -> int:
    return asyncio.run(async_main())

if __name__ == '__main__':
    sys.exit(main())
