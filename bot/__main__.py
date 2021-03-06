import os

import psycopg2
from loguru import logger
from dotenv import load_dotenv
load_dotenv()

try:
    try:
        from .pgsql import ConnectionWrapper
        con = ConnectionWrapper()
        con.ensure_base_tables()
        if os.getenv('DB_DEBUG', None):
            logger.debug(con.exists(('channel_id', 989976538067918968), table='vc_data'))
    except psycopg2.OperationalError:
        raise

    try:
        if not os.getenv('DB_DEBUG', None):
            from bot.bot import PVCBot

            bot_ = PVCBot(debug_guilds=[
                829265067073339403,  # gala
            ], con_=con)
            token = os.getenv("PVC_TOKEN", None)
            if token is None:
                raise ValueError("TOKEN not found, check env file")
            bot_.load_custom_cogs()
            bot_.run(token)
    except ConnectionError as e:
        logger.critical(f"Unable to connect to Discord. exit error {e}")
        raise
    except ImportError:
        raise ImportError("Unable to import PVC_bot")

except KeyboardInterrupt as e:
    logger.info(f"Exiting app...")
    exit(0)

except BaseException as e:
    logger.critical(f"Error {e} happened when stating the bot ")
    raise


