import os
from collections import defaultdict

import pandas as pd
from loguru import logger
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


load_dotenv()


class DatagemsPostgres:
    def __init__(self, database: str, schema: str):
        """
        Initialize the datagems database connector.
        """
        self.specific_schema = schema

        self.connection_uri = (
            f"postgresql+psycopg2://{os.getenv('DATAGEMS_POSTGRES_USERNAME')}:"
            f"{os.getenv('DATAGEMS_POSTGRES_PASSWORD')}@{os.getenv('DATAGEMS_POSTGRES_HOST')}:"
            f"{os.getenv('DATAGEMS_POSTGRES_PORT')}/{database}"
        )

        conn_args = {
            "options": f" -c search_path={self.specific_schema}"
            if self.specific_schema
            else ""
        }

        self.engine = create_engine(self.connection_uri, connect_args=conn_args)

    def execute(self, sql) -> pd.DataFrame | dict:
        """
        Execute a given SQL query.

        Note: By default the limit parameter is applied ignoring any limit set in the query from the user.
        To avoid applying a limit, set the limit parameter to -1.

        Args:
            sql: the sql query

        Returns:
            results: the results of the query or a dictionary with an error message
        """

        try:
            with self.engine.begin() as conn:
                df = pd.read_sql(text(sql), con=conn)
            conn.close()
            self.engine.dispose()
        except SQLAlchemyError as e:
            logger.error(f"sqlalchemy error {str(e.__dict__['orig'])}")
            return {"error": str(e.__dict__["orig"])}
        except RuntimeError as e:
            logger.error(f"runtime error {str(e)}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"other exception: {e} {sql}")
            return {"error": f"Something went wrong with your query. Error: {e}"}
        return df

    def get_tables_and_columns(self, blacklist_tables: list = []) -> dict:
        """
        Return the schema of the database

        Args:
            blacklist_tables: the tables to exclude from the results


        Examples:
            ```
            {
                'tables': ['table1', 'table2'],
                'columns': ['table1.column1', 'table1.column2', 'table2.column1'],
                'table': {
                    'table1': [0, 1],
                    'table2': [2]
                }
            }
            ```
        """
        q = f"""
            SELECT table_name,column_name
            FROM information_schema.COLUMNS
            WHERE table_schema in ('{self.specific_schema}')
        """

        results = self.execute(q)
        return self._parse_tables_and_columns(results)

    @staticmethod
    def _parse_tables_and_columns(results) -> dict:
        column_id = 0
        parsed = {"tables": [], "columns": [], "table": {}}

        for _, row in results.iterrows():
            table, column = row

            if table not in parsed["tables"]:
                parsed["tables"].append(table)
                parsed["table"][table] = []

            parsed["columns"].append(table + "." + column)
            parsed["table"][table].append(column_id)

            column_id += 1

        return parsed

    def get_types_of_db(self) -> dict:
        """
        Return the types of the columns of the database
        """
        ret_types = defaultdict(dict)
        query = f"""
            SELECT table_name, column_name, data_type
            FROM information_schema.COLUMNS
            WHERE table_schema='{self.specific_schema if self.specific_schema else 'public'}'
              AND table_name NOT ILIKE 'pg_%'
              AND table_name NOT ILIKE 'sql_%';
        """
        results = self.execute(query)
        for _, row in results.iterrows():
            table, column, data_type = row
            data_type = data_type.replace("character varying", "varchar").upper()
            ret_types[table][column] = data_type

        return ret_types

    def get_primary_keys(self) -> dict:
        """
        Return the primary keys of the database
        """
        ret_pks = defaultdict(list)
        query = f"""
                SELECT
                    tc.table_name,
                    kcu.column_name
                FROM
                    information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                WHERE tc.constraint_type = 'PRIMARY KEY'
                    and tc.table_schema = '{self.specific_schema if self.specific_schema else 'public'}' ;
            """

        results = self.execute(query)
        for _, row in results.iterrows():
            table, column = row
            ret_pks[table].append(column)

        return ret_pks

    def get_foreign_keys(self) -> dict:
        """
        Return the foreign keys of the database
        """
        ret_foreign_keys = {}
        query = f"""
        SELECT
            tc.table_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema='{self.specific_schema if self.specific_schema else 'public'}'
        """
        results = self.execute(query)
        for _, row in results.iterrows():
            table, column, foreign_table, foreign_column = row
            if table in ret_foreign_keys and column in ret_foreign_keys[table]:
                ret_foreign_keys[table][column].append(
                    {
                        "foreign_table": foreign_table,
                        "foreign_column": foreign_column,
                    }
                )
            else:
                ret_foreign_keys[table] = {
                    column: [
                        {
                            "foreign_table": foreign_table,
                            "foreign_column": foreign_column,
                        }
                    ]
                }

        return ret_foreign_keys

    def get_joins(self) -> dict:
        """
        Return the joins for the database

        Examples:
            ```
            {
                'table1': {
                    'table2': 'table1.column1=table2.column1',
                    'table3': 'table1.column2=table3.column2'
                },
            }
            ```
        """
        query = f"""
        SELECT
            tc.table_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM
            information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY' and tc.table_schema in ('{self.specific_schema}')
        """

        results = self.execute(query)
        return self._parse_joins(results)

    @staticmethod
    def _parse_joins(results) -> dict:
        joins = {}
        for _, join in results.iterrows():
            for i in [0, 2]:
                thisTable = join[i]
                otherTable = join[0] if i == 2 else join[2]

                if thisTable not in joins:
                    joins[thisTable] = {}

                if otherTable not in joins[thisTable]:
                    joins[thisTable][otherTable] = []

                condition = join[0] + "." + join[1] + "=" + join[2] + "." + join[3]
                joins[thisTable][otherTable].append(condition)

        for tableA, valA in joins.items():
            for tableB, valB in valA.items():
                joins[tableA][tableB] = " AND ".join(valB)

        return joins


if __name__ == "__main__":
    print(DatagemsPostgres(database="ds_era5_land", schema="public").get_tables_and_columns())
