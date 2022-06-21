import psycopg2
from loguru import logger
from typing import Annotated


class ConnectionWrapper:
    try:

        logger.debug("Trying to connect to db")
        con = psycopg2.connect(
            database="bot_pvc_db",
            user="postgres",
            password="postgres",
            host="127.0.0.1",
            port="5432"
        )
        logger.debug(
            f"Connected to db {con.info.dbname} with user {con.info.user}"
        )

    except psycopg2.OperationalError:
        logger.critical("Unable to Connect to DB")
        raise

    except ImportError:
        logger.critical("Unable to Import psycopg2")
        raise

    def execute_query(self, query: str, commit: bool = True) -> psycopg2.extensions.cursor:
        cur = self.con.cursor()
        cur.execute(query.strip())
        if commit:
            self.con.commit()
        return cur

    def ensure_base_tables(self):
        self.execute_query("""
            CREATE TABLE IF NOT EXISTS bot_data (
            id serial PRIMARY KEY,
            user_id bigint UNIQUE NOT NULL,
            channel_id bigint UNIQUE NOT NULL
            );
        """)
        self.execute_query("""
            CREATE TABLE IF NOT EXISTS vc_data (
            id serial PRIMARY KEY,
            channel_id bigint UNIQUE NOT NULL,
            type VARCHAR (10) NOT NULL,
            guild_id bigint NOT NULL
            );
        """)

    def drop_table(self):
        try:
            self.execute_query("""DROP TABLE bot_data""")
        except psycopg2.errors.UndefinedTable:
            logger.debug("Table Does not exits.. skipping")

    def get(self, user_id: int | None = None, channel_id: int | None = None):
        if user_id or channel_id:
            return self.execute_query(f"""SELECT channel_id, user_id from bot_data 
            WHERE {'user_id' if user_id else 'channel_id'}={user_id if user_id else channel_id}
            """, commit=False)

    def get_vc_data(self, channel_id: int | None = None, guild_id: int | None = None):
        if channel_id:
            return self.execute_query(f"""SELECT type from vc_data 
            WHERE channel_id={channel_id}
            """, commit=False)
        elif guild_id:
            return self.execute_query(f"""SELECT channel_id from vc_data 
            WHERE guild_id={guild_id}
            """, commit=False)

    def insert(self,
               user_id: int,
               channel_id: int,
               table: Annotated[str, "bot_data", "no_owner"] = 'bot_data',
               update: str = 'channel_id'
               ):
        if update == 'channel_id':
            return self.execute_query(f"""INSERT INTO {table} (user_id, channel_id) values({user_id}, {channel_id})
            on conflict (user_id) do update set channel_id={channel_id}
            """)
        elif update == 'user_id':
            return self.execute_query(f"""INSERT INTO {table} (user_id, channel_id) values({user_id}, {channel_id})
            on conflict (channel_id) do update set user_id={user_id}
            """)

    def insert_main(self, channel_id: int, type_: str, guild_id: int):
        return self.execute_query(f"""INSERT INTO vc_data (channel_id, type, guild_id)
        values({channel_id},'{type_}', {guild_id})
        on conflict (channel_id) do nothing 
        """)

    def delete(self, user_id: int = None, channel_id: int = None, **kwargs):
        if kwargs.get('vc-data', None):
            return self.execute_query(f"""DELETE from vc_data
            WHERE channel_id={channel_id}
            """)
        elif user_id or channel_id:
            return self.execute_query(f"""DELETE from bot_data
            WHERE {'user_id' if user_id else 'channel_id'}={user_id if user_id else channel_id}
            """)

