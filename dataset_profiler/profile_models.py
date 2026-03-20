import json
import os
import uuid
from collections import defaultdict
from typing import List

from dataset_profiler.dataset_specification import (
    DatasetSpecification,
)
from dataset_profiler.profile_components.constants import (
    CONTEXT_TEMPLATE,
    REFERENCES_TEMPLATE,
)
from dataset_profiler.profile_components.dateset_top_level import (
    DatasetTopLevel,
)
from dataset_profiler.profile_components.distribution import (
    DistributionFileObject,
    DistributionFileSet,
    DistributionDatabaseConnection,
    get_distribution_of_file_object,
    get_distribution_of_file_set,
    get_distribution_of_database_connection,
    get_distributions_of_tables_in_db, get_file_objects_of_file_set,
)
from dataset_profiler.profile_components.record_set.csv.csv_record_set import CSVRecordSet
from dataset_profiler.profile_components.record_set.db.db_distribution import (
    get_added_distributions,
    get_db_ids_from_distributions,
)
from dataset_profiler.profile_components.record_set.db.db_record_set import DBRecordSet
from dataset_profiler.profile_components.record_set.pdf.pdf_record_set import PdfRecordSet
from dataset_profiler.profile_components.record_set.record_set_abc import (
    RecordSet,
)
from dataset_profiler.profile_components.record_set.record_set_extractor import (
    extract_record_sets_of_file_objects,
    extract_record_sets_of_file_sets,
    extract_record_sets_of_database_connections, extract_record_sets_of_file_objects_in_file_sets,
)
from dataset_profiler.profile_components.record_set.text.text_record_set import TextRecordSet
from dataset_profiler.utilities import get_file_objects
from dataset_profiler.configs.config_logging import logger


class DatasetProfile:
    def __init__(self, dataset_specification: dict):
        self.dataset_specification = DatasetSpecification(dataset_specification)
        self.data_connectors = self.dataset_specification.data_connectors
        self.record_sets_per_file_object = {}
        self.distribution_path = None
        for connector in self.data_connectors:
            if (
                connector["type"] == "RawDataPath"
                and self.distribution_path is not None
            ):
                logger.warning(
                    f"Only one RawDataPath connector is supported. "
                    f"Using {self.distribution_path} and ignoring {connector['path']}."
                )
                continue
            if connector["type"] == "RawDataPath":
                self.distribution_path = connector["dataset_id"]

        if self.distribution_path is not None:
            self.file_objects, self.file_sets = get_file_objects(self.distribution_path)
        else:
            self.file_objects, self.file_sets = [], []
        self.databases_objects = [
            {
                "database_name": connector["database_name"],
                "file_object_id": str(uuid.uuid4()),
            }
            for connector in self.data_connectors
            if connector["type"] == "DatabaseConnection"
        ]

        self.dataset_top_level = DatasetTopLevel(
            dataset_id=self.dataset_specification.id,
            name=self.dataset_specification.name,
            description=self.dataset_specification.description,
            conforms_to="",
            cite_as=self.dataset_specification.citeAs,
            license=self.dataset_specification.license,
            url=self.dataset_specification.url,
            version="",
            headline=self.dataset_specification.headline,
            keywords=self.dataset_specification.keywords,
            field_of_science=self.dataset_specification.fieldOfScience,
            in_language=self.dataset_specification.inLanguage,
            country=self.dataset_specification.country,
            date_published=self.dataset_specification.datePublished,
            access=self.dataset_specification.access,
            uploaded_by=self.dataset_specification.uploadedBy,
        )

        # Distribution
        self.distributions: (
            List[
                DistributionFileObject
                | DistributionFileSet
                | DistributionDatabaseConnection
            ]
            | None
        ) = None
        self.file_sets_distributions = None
        self.database_connector_distributions = None
        self.file_object_distributions = None
        self.file_object_of_set_distributions = None

        # RecordSet
        self.record_sets: List[RecordSet] | None = None

    def extract_distributions(
        self,
    ) -> List[
        DistributionFileObject | DistributionFileSet | DistributionDatabaseConnection
    ]:
        file_object_distributions = []
        if self.distribution_path is not None:
            file_object_distributions = [
                dist
                for dist in [
                    get_distribution_of_file_object(
                        self.distribution_path + file_object["path"], file_object["id"]
                    )
                    for file_object in self.file_objects
                ]
                if dist is not None  # Filter out unsupported file types
            ]
        database_connector_distributions = [
            get_distribution_of_database_connection(
                connection_id=db_connector["file_object_id"],
                database_name=db_connector["database_name"],
            )
            for db_connector in self.databases_objects
        ]
        database_table_distributions = []
        for db_distribution in database_connector_distributions:
            database_table_distributions += get_distributions_of_tables_in_db(
                database_name=db_distribution.name,
                database_distribution_id=db_distribution.id,
            )
        database_connector_distributions += database_table_distributions

        file_sets_distributions = []
        file_object_of_set_distributions = []
        if self.distribution_path is not None:
            for file_set in self.file_sets:
                # Get the distribution for the current file set
                dist = get_distribution_of_file_set(
                    self.distribution_path + file_set["path"],
                    file_set["id"]
                )
                if dist is not None:
                    file_sets_distributions.append(dist)

                    # Fetch objects for this specific distribution
                    file_objects = get_file_objects_of_file_set(
                        contained_in_id=dist.id,
                        file_set_path=self.distribution_path + file_set["path"]
                    )

                    # Flatten the list of file objects and add them to the main list of distributions
                    for item in file_objects:
                        file_object_of_set_distributions.append(item)

        self.file_sets_distributions = file_sets_distributions
        self.database_connector_distributions = database_connector_distributions
        self.file_object_distributions = file_object_distributions
        self.file_object_of_set_distributions = file_object_of_set_distributions

        return (
            file_sets_distributions
            + database_connector_distributions
            + file_object_distributions
            + file_object_of_set_distributions
        )

    def extract_record_sets(self) -> List[RecordSet]:
        record_sets = []

        if self.distribution_path is not None:
            record_sets += extract_record_sets_of_file_objects(
                self.file_objects, self.distribution_path
            )

        if self.distributions is not None:
            record_sets += extract_record_sets_of_database_connections(
                self.databases_objects, self.distributions
            )

        if self.file_object_of_set_distributions is not None:
            record_sets += extract_record_sets_of_file_objects_in_file_sets(
                self.file_object_of_set_distributions, self.distribution_path
            )

        return record_sets

    def to_dict_light(self):
        if self.distributions is None:
            self.distributions = self.extract_distributions()
        return {
            "@context": {**CONTEXT_TEMPLATE, **REFERENCES_TEMPLATE},
            **self.dataset_top_level.to_dict(),
            "distribution": [
                distribution.to_dict() for distribution in self.distributions
            ],
        }

    def to_dict(self):
        if self.distributions is None:
            self.distributions = self.extract_distributions()
        if self.record_sets is None:
            self.record_sets = self.extract_record_sets()

        record_set_list = []
        for record_set in self.record_sets:
            if isinstance(record_set, DBRecordSet):
                # In case of a relational database we want to flatten the tables of the db into independent tables
                record_set_list.extend(record_set.to_dict())
            else:
                record_set_list.append(record_set.to_dict())
        profile_dict = {
            "@context": {**CONTEXT_TEMPLATE, **REFERENCES_TEMPLATE},
            **self.dataset_top_level.to_dict(),
            "distribution": [
                distribution.to_dict() for distribution in self.distributions
            ],
            "recordSet": record_set_list,
        }

        # db_ids_with_file_obj_ids = get_db_ids_from_distributions(
        #     profile_dict["distribution"]
        # )
        # for db_id, file_obj_id in db_ids_with_file_obj_ids:
        #     profile_dict["distribution"].extend(
        #         get_added_distributions(profile_dict["recordSet"], db_id, file_obj_id)
        #     )

        for record_set in self.record_sets:
            if record_set.inject_distribution:
                profile_dict["distribution"].append(record_set.inject_distribution)

        return profile_dict

    def to_dict_cdd(self):
        if self.distributions is None:
            self.distributions = self.extract_distributions()
        if self.record_sets is None:
            self.record_sets = self.extract_record_sets()
        distributions_and_record_sets = match_distributions_with_record_sets(self.distributions, self.record_sets)

        files = []
        for matched_dist_and_record_set in distributions_and_record_sets:
            dist = matched_dist_and_record_set["distribution"]
            record_sets = matched_dist_and_record_set["record_sets"]

            if dist.encoding_format in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                       "application/vnd.ms-excel"]:
                tables = [{
                    "name": record_set.name,
                    "description": record_set.description,
                    "columns": [column.to_dict_cdd() for column in record_set.fields]
                } for record_set in record_sets]
                files.append(
                    {
                        "file_object_id": dist.id,
                        "original_format": "xlsx",
                        "source_file": dist.content_url,
                        "name": dist.name,
                        "description": dist.description,
                        "keywords": [],
                        "tables": tables
                    }
                )
            else:
                if len(record_sets) > 1:
                    logger.error("Unexpected length of records sets when generating CDD profile",
                                 file_object_id=dist.id, num_record_sets=len(record_sets))
                files.append(record_sets[0].to_dict_cdd())


        return {
            **self.dataset_top_level.to_dict_cdd(),
            "files": files
        }


    def to_json_str(self):
        return json.dumps(self.to_dict(), indent=3)


def match_distributions_with_record_sets(distributions, record_sets) -> list[dict]:
    matched_distributions = {}
    distribution_id_index = {distribution.id: distribution for distribution in distributions}
    for record_set in record_sets:
        if (isinstance(record_set, CSVRecordSet) or isinstance(record_set, PdfRecordSet)
                or isinstance(record_set, TextRecordSet)):
            distribution = distribution_id_index.get(record_set.file_object_id)
            if record_set.file_object_id not in matched_distributions:
                matched_distributions[record_set.file_object_id] = {
                    "distribution": distribution,
                    "record_sets": [record_set],
                }
            else:
                matched_distributions[record_set.file_object_id]["record_sets"].append(record_set)
        elif isinstance(record_set, DBRecordSet):
            db_connection_distribution = distribution_id_index.get(record_set.file_object_id)
            matched_distributions[record_set.file_object_id] = {
                "distribution": db_connection_distribution,
                "record_sets": [record_set],
            }
        else:
            print("Not covered yet")

    return list(matched_distributions.values())
