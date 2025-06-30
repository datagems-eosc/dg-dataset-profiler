from typing import Dict

from dataset_profiler.profile_components.record_set.db.database_connector import (
    DatagemsPostgres,
)
from dataset_profiler.profile_components.record_set.db.get_db_schema import (
    obtain_schema_from_db,
)
from dataset_profiler.profile_components.record_set.record_set_abc import (
    ColumnField,
    RecordSet,
)
from dataset_profiler.utilities import find_column_type_in_db


class DBRecordSet(RecordSet):
    def __init__(
        self,
        distribution_path: str,
        file_object: str,
        db_name: str,
        db_specific_schema: str,
    ):
        self.distribution_path = distribution_path
        self.file_object = file_object.split("/")[-1]
        self.db_name = db_name
        self.db_specific_schema = db_specific_schema
        # # self.type = "dg:RelationalDatabase"
        # self.name = self.file_object.split(".")[-2]
        # self.description = ""
        # self.key = {"@id": self.name}
        self.tables = self.extract_fields()

    def extract_fields(self):
        db = DatagemsPostgres(self.db_specific_schema)
        db_schema = obtain_schema_from_db(db, sample_size=3)

        tables = []
        for table in db_schema:
            tables.append(DBTableField(table, self.file_object))
        return tables

    def to_dict(self):
        return [table.to_dict() for table in self.tables]
        # return {
        #     # "@type": self.type,
        #     # "name": self.name,
        #     # "description": self.description,
        #     # "key": self.key,
        #     "tables": [table.to_dict() for table in self.tables],
        # }


class DBTableField:
    def __init__(self, table: Dict, file_object: str):
        self.table = table
        self.file_object = file_object
        self.type = "cr:RecordSet"
        self.id = self._get_table_id(file_object, table)
        self.name = self._get_table_id(file_object, table)
        # self.rowsNumb = ""
        self.description = ""
        self.key = {"@id": self._get_table_id(file_object, table)}
        self.fields = self.extract_fields()

    @staticmethod
    def _get_table_id(file_object, table):
        return file_object + "/" + table["table_name"]

    def extract_fields(self):
        fields = []
        for column in self.table["columns"]:
            fields.append(
                DBColumnField(column, self.table["table_name"], self.file_object)
            )

        return fields

    def to_dict(self):
        return {
            "@type": self.type,
            "name": self.name,
            # "rowsNumb": self.rowsNumb,
            "description": self.description,
            "key": self.key,
            "field": [field.to_dict() for field in self.fields],
        }


class DBColumnField(ColumnField):
    def __init__(self, column, table_name: str, file_object: str):
        self.type = "cr:Field"
        self.id = table_name + "/" + column["column"]
        self.name = table_name + "/" + column["column"]
        self.description = ""
        self.dataType = find_column_type_in_db(column["data_type"])
        self.key = {"@id": table_name + "/" + column["column"]}
        self.source = {
            "fileObject": {"@id": file_object.split("/")[-1]},
            "column": column["column"],
        }
        self.sample = [f"{value}" for value in column["values"]]

    def to_dict(self):
        return {
            "@type": self.type,
            "@id": self.id,
            "name": self.name,
            "description": self.description,
            "dataType": self.dataType,
            "key": self.key,
            "source": self.source,
            "sample": self.sample,
        }
