from bluemoon.bot import run_bot
from bluemoon.config import load_settings


if __name__ == "__main__":
    run_bot(load_settings())
