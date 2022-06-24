from typing import Any

import psycopg2
from psycopg2 import sql
from loguru import logger
import os


class ConnectionWrapper:
    try:

        logger.debug("Trying to connect to db")
        con = psycopg2.connect(
            database="bot_pvc_db",
            user="postgres",
            password="postgres",
            host=os.getenv("PG_HOST", "db"),
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

    def execute_query(self, query: str | sql.Composable, commit: bool = True) -> psycopg2.extensions.cursor:
        cur = self.con.cursor()
        cur.execute(query)
        if commit:
            self.con.commit()
        return cur

    def ensure_base_tables(self):
        self.execute_query("""
            CREATE TABLE IF NOT EXISTS bot_data (
            id serial PRIMARY KEY,
            user_id bigint UNIQUE NOT NULL,
            channel_id bigint UNIQUE NOT NULL,
            msg_id bigint UNIQUE NOT NULL
            );
        """)
        self.execute_query("""
            CREATE TABLE IF NOT EXISTS vc_data (
            id serial PRIMARY KEY,
            channel_id bigint UNIQUE NOT NULL,
            type VARCHAR (10) NOT NULL,
            guild_id bigint NOT NULL,
            name_format varchar (50)
            );
        """)

    def drop_table(self):
        try:
            self.execute_query("""DROP TABLE bot_data""")
        except psycopg2.errors.UndefinedTable:
            logger.debug("Table Does not exits.. skipping")

    def get(self, user_id: int | None = None, channel_id: int | None = None, msg_id: int | None = None,
            all_: bool = False) -> psycopg2.extensions.cursor:
        execute_sql = ''
        if all_:
            execute_sql = f"""SELECT channel_id, user_id, msg_id from bot_data"""

        if user_id or channel_id or msg_id:
            execute_sql = f"""SELECT channel_id, user_id, msg_id from bot_data 
            WHERE {'user_id' if user_id else 'channel_id' if channel_id else 'msg_id'}={user_id if user_id else channel_id if channel_id else msg_id}
            """
        if execute_sql:
            return self.execute_query(execute_sql, commit=False)

    def get_vc_data(self, where: tuple, get: str):
        if len(where) != 2:
            raise ValueError("Invalid key mapping passed")
        return self.execute_query(f"""SELECT {get} from vc_data 
        WHERE {where[0]}={where[1]}
        """, commit=False)

    def insert(self,
               user_id: int,
               channel_id: int,
               msg_id: int | None = None,
               update: str = 'channel_id'
               ):
        if update == 'channel_id':
            return self.execute_query(
                f"""INSERT INTO bot_data (user_id, channel_id, msg_id) values({user_id}, {channel_id}, {msg_id if msg_id else 'NULL'})
            on conflict (user_id) do update set channel_id={channel_id}
            """)
        elif update == 'user_id':
            return self.execute_query(
                f"""INSERT INTO bot_data (user_id, channel_id, msg_id) values({user_id}, {channel_id}, {msg_id if msg_id else 'NULL'})
            on conflict (channel_id) do update set user_id={user_id}
            """)

    def insert_main(self, channel_id: int, type_: str, guild_id: int, name_format: str = None):
        return self.execute_query(f"""INSERT INTO vc_data (channel_id, type, guild_id, name_format)
        values({channel_id},'{type_}', {guild_id}, '{name_format if name_format else 'NULL'}')
        on conflict (channel_id) do nothing 
        """)

    def update(self, table: str, where: tuple[str, Any], returning: str | None = None, **kwargs):
        update_fields = []
        for column, value in kwargs.items():
            update_fields.append(sql.SQL("=").join(
                [sql.Identifier(str(column)), sql.Literal(value)]
            ))

        format_kwargs = {
            'table': sql.Identifier(table),
            'update_fields': sql.SQL(',').join(update_fields),
            'condition': sql.SQL('=').join([sql.Identifier(where[0]), sql.Literal(where[1])]),
        }
        if returning:
            format_kwargs.update({'returning': sql.Identifier(returning)})

        query = sql.SQL(
            """UPDATE {table} SET {update_fields} where {condition} """
            + ("RETURNING (SELECT {returning} FROM {table} WHERE {condition})" if returning else '')
        ).format(**format_kwargs)

        return self.execute_query(query)

    def exists(self, where: tuple[str, Any],  table: str = 'bot_data') -> bool:
        # SELECT exists (SELECT 1 FROM table WHERE column = <value> LIMIT 1);
        query = sql.SQL(
            "SELECT exists (SELECT 1 FROM {table} WHERE {condition} LIMIT 1)"
        ).format(
            table=sql.Identifier(table),
            condition=sql.SQL('=').join([
                sql.Identifier(where[0]),
                sql.Literal(where[1])
            ])
        )
        with self.execute_query(query, commit=False) as curr:
            return curr.fetchone()[0]

    def delete(self, user_id: int = None, channel_id: int = None, **kwargs):
        if kwargs.get('vc-data', None):
            return self.execute_query(f"""DELETE from vc_data
            WHERE channel_id={channel_id}
            """)
        elif user_id or channel_id:
            return self.execute_query(f"""DELETE from bot_data
            WHERE {'user_id' if user_id else 'channel_id'}={user_id if user_id else channel_id}
            """)
