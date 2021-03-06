from typing import Any, Optional, Literal

import psycopg2
from psycopg2 import sql
from loguru import logger
import os
from typing import TypedDict


class ValidColumns(TypedDict, total=False):
    user_id: int
    channel_id: int
    guild_id: int
    parent_channel_id: int
    msg_id: int
    type: str
    name_format: str


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
            msg_id bigint UNIQUE default null,
            parent_channel_id bigint not null
            );
        """)
        self.execute_query("""
            CREATE TABLE IF NOT EXISTS vc_data (
            id serial PRIMARY KEY,
            channel_id bigint UNIQUE NOT NULL,
            type VARCHAR (10) NOT NULL,
            guild_id bigint NOT NULL,
            name_format varchar (50),
            activities_enabled bool default false not null
            );
        """)
        self.execute_query("""
            CREATE TABLE IF NOT EXISTS increment_vc_data (
            parent_channel_id bigint primary key ,
            child_list text default '[0]'
            );
        """)

    def __drop_table(self):
        try:
            self.execute_query("""DROP TABLE bot_data""")
        except psycopg2.errors.UndefinedTable:
            logger.debug("Table Does not exits.. skipping")

    def get(
            self,
            columns: tuple[str, ...],
            conditions: ValidColumns | None = None,
            table: Literal["bot_data", 'vc_data', "increment_vc_data"] = 'bot_data',
    ) -> psycopg2.extensions.cursor:
        """
        A generic get function to get values from db

        :param columns:
        :param conditions:
        :param table:
        :return: psycopg2.Cursor
        """
        format_kwargs = {
            'columns': sql.SQL(',').join([sql.Identifier(i) for i in columns])
            if columns[0] != '*' else sql.SQL("*"),

            'table': sql.Identifier(table),
        }
        if conditions:
            format_kwargs.update(
                {
                    'conditions': sql.SQL(',').join(
                        [
                            sql.SQL('=').join((sql.Identifier(key), sql.Literal(value)))
                            for key, value in conditions.items()
                        ]
                    )
                }
            )
        query = sql.SQL(
            "SELECT {columns} FROM {table} " +
            ("where {conditions}" if conditions else '')
        ).format(**format_kwargs)

        return self.execute_query(query, commit=False)

    def get_vc_data(self, columns: tuple[str, ...],
                    condition: dict[str, Any] | None = None) -> psycopg2.extensions.cursor:
        """
        A generic function to get values from table vc_data

        :param columns:
        :param condition:
        :return:
        """
        return self.get(columns, condition, 'vc_data')

    def insert(self,
               user_id: int,
               channel_id: int,
               parent_channel_id: int,
               msg_id: int | None = None,
               update: str = 'channel_id'
               ):
        if update == 'channel_id':
            return self.execute_query(
                f"""INSERT INTO bot_data (user_id, channel_id, msg_id, parent_channel_id) values({user_id}, {channel_id}, {msg_id if msg_id else 'NULL'}, {parent_channel_id})
            on conflict (user_id) do update set channel_id={channel_id}
            """)
        elif update == 'user_id':
            return self.execute_query(
                f"""INSERT INTO bot_data (user_id, channel_id, msg_id, parent_channel_id) values({user_id}, {channel_id}, {msg_id if msg_id else 'NULL'}, {parent_channel_id})
            on conflict (channel_id) do update set user_id={user_id}
            """)

    def insert_main(self,
                    channel_id: int,
                    type_: str,
                    guild_id: int,
                    name_format: str = None,
                    activities_enabled: bool | None = None
                    ):
        return self.execute_query(f"""INSERT INTO vc_data (channel_id, type, guild_id, name_format, activities_enabled)
        values({channel_id},'{type_}', {guild_id}, '{name_format if name_format else 'NULL'}', {activities_enabled})
        on conflict (channel_id) do nothing 
        """)

    def insert_inc_data(self, parent_channel_id: int):
        query = sql.SQL("INSERT INTO increment_vc_data (parent_channel_id) VALUES ({parent_channel_id})").format(
            parent_channel_id=sql.Literal(parent_channel_id)
        )
        return self.execute_query(query)

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

    def exists(self, where: tuple[str, Any], table: str = 'bot_data') -> bool:
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

    def delete(self, table: str, conditions: ValidColumns):
        # DELETE
        # from vc_data
        # WHERE channel_id={channel_id}

        query = sql.SQL("DELETE from {table} where {conditions}").format(
            table=sql.Identifier(table),
            conditions=sql.SQL(',').join(
                [
                    sql.SQL('=').join((sql.Identifier(key), sql.Literal(value)))
                    for key, value in conditions.items()
                ])
        )
        return self.execute_query(query)
