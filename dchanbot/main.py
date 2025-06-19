"""Main entry point for Dennou-Chan Discord Bot

This script initializes and starts the Discord bot by loading environment
variables and passing configuration paths to the bot instance.
"""

import sys

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

def main() -> int:
    """Main function to initialize and start the bot

    Reads configuration and data directory paths from environment variables,
    creates a bot instance, and starts it.

    Returns:
        int: Exit status code.
    """

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
