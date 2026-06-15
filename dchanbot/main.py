"""Main entry point for Dennou-Chan Discord Bot

This script initializes and starts the Discord bot by loading environment
variables and passing configuration paths to the bot instance.
"""

import sys
import logging
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

def main() -> int:
    """Main function to initialize and start the bot

    Reads configuration and data directory paths from environment variables,
    creates a bot instance, and starts it.

    Returns:
        int: Exit status code.
    """

    setup_logging()

    confroot_str = os.environ.get("DBOT_CONFIG_DIR")
    dataroot_str = os.environ.get("DBOT_DATA_DIR")
    bot = DChanBot(
        confdir = Path(confroot_str),
        datadir = Path(dataroot_str)
    )
    bot.run()   # <- This call blocks until bot shutdown, must be called last!

    return 0

if __name__ == '__main__':
    sys.exit(main())
