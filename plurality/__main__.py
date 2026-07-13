"""Entry point: python -m plurality"""

import asyncio

from plurality.bot import run_bot


def main():
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()