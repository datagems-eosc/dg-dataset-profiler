import re
from pathlib import Path
from random import sample

import pandas.api.types as ptypes


def find_column_type_in_csv(column):
    # Case of explicit type
    if ptypes.is_integer_dtype(column):
        return "sc:Integer"
    elif ptypes.is_float_dtype(column):
        return "sc:Float"
    elif ptypes.is_datetime64_dtype(column):
        return "sc:Date"

    # Case of implicit type
    type_regexes = {
        "float": re.compile(r"^\d+\.\d+$"),
        "int": re.compile(r"^\d+$"),
        "date": re.compile(r"^\d\d\d\d-\d\d-\d\d$"),
    }
    type_appearances = {
        "float": 0,
        "int": 0,
        "date": 0,
    }

    # Pick three random rows
    num_rows = len(column)
    r1, r2, r3 = sample(range(0, num_rows), 3)
    picked_indices = [r1, r2, r3]

    # For each row update the appearances dictionary if value is accepted by the regex
    for index in picked_indices:
        for type, regex in type_regexes.items():
            value = column.loc[index]
            if regex.match(value) is not None:
                type_appearances[type] += 1
                continue

    if (
        type_appearances["float"] == 0
        and type_appearances["int"] == 0
        and type_appearances["date"] == 0
    ):
        return "sc:Text"
    else:
        result_type = max(type_appearances, key=type_appearances.get)  # type: ignore

        match result_type:
            case "float":
                return "sc:Float"
            case "int":
                return "sc:Integer"
            case "date":
                return "sc:Date"


def find_column_type_in_db(db_type):
    match db_type:
        case "INTEGER":
            return "sc:Integer"
        case "FLOAT":
            return "sc:Float"
        case "DATE":
            return "sc:Date"
        case "TEXT":
            return "sc:Text"


def get_file_objects(distribution_path):
    try:
        path = Path(distribution_path)

        file_objects = [item.name for item in path.iterdir() if item.is_file()]
        file_sets = [item.name for item in path.iterdir() if item.is_dir()]

        return file_objects, file_sets
    except FileNotFoundError:
        return f"The path '{distribution_path}' does not exist."

    # @TODO add utilities for text_record_set
