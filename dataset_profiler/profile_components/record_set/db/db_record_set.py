import uuid
from typing import Dict

from dataset_profiler.profile_components.record_set.db.database_connector import (
    DatagemsPostgres,
)
from dataset_profiler.profile_components.record_set.db.db_calculate_statistics import calculate_statistics_of_db
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
        file_object_id: str,
        db_name: str,
        db_specific_schema: str,
    ):
        super().__init__()
        self.distribution_path = distribution_path
        self.file_object = file_object.split("/")[-1]
        self.file_object_id = file_object_id
        self.db_name = db_name
        self.db_specific_schema = db_specific_schema
        # # self.type = "dg:RelationalDatabase"
        # self.name = self.file_object.split(".")[-2]
        # self.description = ""
        # self.key = {"@id": self.name}
        self.tables = self.extract_fields()

    def extract_fields(self):
        db = DatagemsPostgres(self.db_name, self.db_specific_schema)
        db_schema = obtain_schema_from_db(db, sample_size=10)

        tables = []
        for table in db_schema:
            tables.append(DBTableField(table, self.file_object, self.file_object_id, db))
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
    def __init__(self, table: Dict, file_object: str, file_object_id: str, db_connection: DatagemsPostgres):
        self.table = table
        self.file_object = file_object
        self.type = "cr:RecordSet"
        self.id = str(uuid.uuid4())
        self.name = self._get_table_name(file_object, table)
        self.file_object_id = file_object_id
        # self.rowsNumb = ""
        self.description = ""
        self.connection = db_connection
        # self.key = {"@id": self._get_table_name(file_object, table)}
        self.fields = self.extract_fields()

    @staticmethod
    def _get_table_name(file_object, table):
        return table["table_name"]

    def extract_fields(self):
        fields = []
        for column in self.table["columns"]:
            fields.append(
                DBColumnField(column, self.table["table_name"], self.connection)
            )

        return fields

    def to_dict(self):
        return {
            "@type": self.type,
            "@id": str(uuid.uuid4()),
            "name": self.name,
            # "rowsNumb": self.rowsNumb,
            "description": self.description,
            # "key": self.key,
            "field": [field.to_dict() for field in self.fields],
        }


class DBColumnField(ColumnField):
    def __init__(self, column, table_name: str, connection: DatagemsPostgres):
        self.type = "cr:Field"
        self.id = self.id = str(uuid.uuid4())
        self.name = column["column"]
        self.description = ""
        self.dataType = find_column_type_in_db(column["data_type"])
        self.statistics = calculate_statistics_of_db(self.name, table_name, connection, self.dataType)
        # The distribution part for the table is not created yet in order for it to have an id
        self.source = {
            "fileObject": {"@id": "NOT_YET_SET"},
            "extract": {"column": column["column"]},
        }
        self.sample = [f"{value}" for value in column["values"]]

    def to_dict(self):
        return {
            "@type": self.type,
            "@id": self.id,
            "name": self.name,
            "description": self.description,
            "dataType": self.dataType,
            "source": self.source,
            "sample": self.sample,
            "statistics": self.statistics.to_dict()
        }
