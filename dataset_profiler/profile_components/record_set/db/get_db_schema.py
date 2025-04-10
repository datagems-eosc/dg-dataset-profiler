import string
from collections import defaultdict
from typing import Dict, List

import pandas as pd

from dataset_profiler.profile_components.record_set.db.database_connector import (
    DatagemsPostgres,
)


def filter_out_system_tables(schema: dict) -> dict:
    schema["tables"] = [table for table in schema["tables"] if "pg_stat_" not in table]
    schema["columns"] = [
        column for column in schema["columns"] if "pg_stat_" not in column
    ]

    return schema


def get_list_from_df(df: pd.DataFrame) -> list:
    if df.empty:
        return []
    elif len(df) == 1:
        return [df.squeeze()]
    else:
        return list(df.squeeze())  # df -> series -> list


def insert_types(db: DatagemsPostgres, schema: list) -> None:
    types = db.get_types_of_db()
    for table in schema:
        for column in table["columns"]:
            column["data_type"] = types[table["table_name"]][column["column"]]


def insert_primary_keys(db: DatagemsPostgres, schema: list) -> None:
    pks = db.get_primary_keys()
    for table in schema:
        for column in table["columns"]:
            column["is_pk"] = (
                True if column["column"] in pks[table["table_name"]] else False
            )


def insert_foreign_keys(db: DatagemsPostgres, schema: list) -> None:
    fks = db.get_foreign_keys()
    for table in schema:
        for column in table["columns"]:
            if (
                table["table_name"] not in fks
                or column["column"] not in fks[table["table_name"]]
            ):
                column["foreign_keys"] = []
            else:
                column["foreign_keys"] = fks[table["table_name"]][column["column"]]


def insert_inferred_foreign_keys(schema: list) -> None:
    """
    Infer foreign keys based on the column names.
    If a column name is the same as another table + column, then it is considered as an fk.
    Names are simplified by:
    * Removing the last 's' if it exists (to avoid plurals)
    * Removing the underscores
    * Lowercasing the name

    Note: This method should be called after insert_foreign_keys which inserts the foreign keys from the database.
    """
    possible_foreign_keys = {}

    def simplify_name(column_name: str, table_name: str = None) -> str:
        if column_name.endswith("s"):
            column_name = column_name[:-1]

        if table_name and table_name.endswith("s"):
            table_name = table_name[:-1]

        ret_name = f"{table_name}_{column_name}" if table_name else column_name
        ret_name = ret_name.lower()
        ret_name = ret_name.replace("_", "")

        return ret_name

    for table in schema:
        for column_info in table["columns"]:
            fk_name = simplify_name(column_info["column"], table["table_name"])

            possible_foreign_keys[fk_name] = {
                "table": table["table_name"],
                "column": column_info["column"],
            }

    for table in schema:
        for column_info in table["columns"]:
            # If the column name is the same as another table + column, then it is considered a foreign key
            column_simple_name = simplify_name(column_info["column"])

            if column_simple_name in possible_foreign_keys:
                foreign_key = possible_foreign_keys[column_simple_name]

                if "foreign_keys" not in column_info:
                    column_info["foreign_keys"] = []

                # Check that the foreign key does not already exist
                fk_exists = False
                for fk in column_info["foreign_keys"]:
                    if (
                        fk["foreign_table"] == foreign_key["table"]
                        and fk["foreign_column"] == foreign_key["column"]
                    ):
                        fk_exists = True
                        break

                # Add the fk in the list of foreign keys
                if not fk_exists:
                    column_info["foreign_keys"].append(
                        {
                            "foreign_table": foreign_key["table"],
                            "foreign_column": foreign_key["column"],
                        }
                    )


def split_list_of_tables_cols(tables_cols: List[str]) -> dict:
    """
    The schema is given in a list of [table1.col1, table1.col2, table2.col1, ...]
    We split this list into a dictionary of tables with their columns

    Args:
        tables_cols: The list of tables and columns

    Returns:
        A dictionary with tables and columns
    """
    tables = defaultdict(list)
    for table_col in tables_cols:
        table, column = table_col.split(".")
        tables[table].append(column)

    return tables


def get_sample_values_of_column(
    db: DatagemsPostgres,
    table_name: str,
    column_name: str,
    sample_size: int,
) -> pd.DataFrame:
    """
    Will return <sample_size> distinct values of the column.

    Args:
        db: The database executor object
        table_name: The table name
        column_name: The column name
        sample_size: The sample size to return

    Returns:
        A tuple of a dataframe with the example values.
    """
    # If there are is_categorical_thresh + 1 distinct values, then the column is not considered categorical
    distinct_values = db.execute(
        f'SELECT DISTINCT "{column_name}" FROM "{table_name}" WHERE "{column_name}" IS NOT NULL LIMIT {sample_size}'
    )

    return distinct_values


def detect_special_char(name: str) -> bool:
    """Check if a name has a special character besides alphanumerics and underscores."""
    acceptable_chars = string.ascii_letters + string.digits + "_"

    for char in name:
        if char not in acceptable_chars:
            return True

    return False


def add_quotation_mark(name: str, dialect: str) -> str:
    if not detect_special_char(name):
        # If there are no special characters, return the name as is
        return name
    else:
        return '"' + name + '"'


def add_quotes_to_names(schema: List[Dict], dialect: str) -> List[Dict]:
    for table in schema:
        # Check the table name
        table["table_name"] = add_quotation_mark(table["table_name"], dialect)
        for column in table["columns"]:
            # Check each column name in the table
            column["column"] = add_quotation_mark(column["column"], dialect)
            for foreign_key in column["foreign_keys"]:
                # Check each foreign key table and column connected to current column
                foreign_key["foreign_table"] = add_quotation_mark(
                    foreign_key["foreign_table"], dialect
                )
                foreign_key["foreign_column"] = add_quotation_mark(
                    foreign_key["foreign_column"], dialect
                )

    return schema


def obtain_schema_from_db(
    db: DatagemsPostgres,
    sample_size: int,
    infer_foreign_keys: bool = False,
) -> list:
    """
    Obtain the schema of the database from the database object. The schema is returned in the following format:
    ```
        [
            {
                "table_name": "table1",
                "columns": [
                    {
                        "column": "col1",
                        "values": [1, 2, 3, 4, 5],
                        "data_type": "INTEGER",
                        "is_pk": False,
                        "foreign_keys": [
                            {
                                "foreign_table": "table2",
                                "foreign_column": col3,
                            },
                            ...
                        ],
                    },
                    ...
                ]
            },
            ...
        ]
        ```

    Args:
        db: The database object
        sample_size: The sample size to return if the column is not categorical
        infer_foreign_keys: Whether to infer foreign keys or not based on the column names

    Returns:
        The schema of the database in the above format
    """
    schema = db.get_tables_and_columns()
    schema = filter_out_system_tables(schema)
    tables_with_cols = split_list_of_tables_cols(schema["columns"])

    ret_schema = []
    for table in tables_with_cols.keys():
        table_dict = {
            "table_name": table,
            "columns": [],
        }
        for column in tables_with_cols[table]:
            example_values = get_sample_values_of_column(db, table, column, sample_size)
            table_dict["columns"].append(
                {
                    "column": column,
                    "values": get_list_from_df(example_values),
                }
            )
        ret_schema.append(table_dict)

    insert_types(db, ret_schema)
    insert_primary_keys(db, ret_schema)
    insert_foreign_keys(db, ret_schema)

    if infer_foreign_keys:
        insert_inferred_foreign_keys(ret_schema)

    # Add quotes in table and column names when necessary
    dialect = "postgres"
    ret_schema = add_quotes_to_names(ret_schema, dialect)

    return ret_schema


if __name__ == "__main__":
    # Example usage
    db = DatagemsPostgres(schema="mathe")
    schema = obtain_schema_from_db(db, sample_size=3)
    print(schema)
