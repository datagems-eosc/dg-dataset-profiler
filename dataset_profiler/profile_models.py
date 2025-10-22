import json
import os
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
    get_distribution_of_file_object,
    get_distribution_of_file_set,
)
from dataset_profiler.profile_components.record_set.db.db_distribution import (
    get_added_distributions,
    get_db_ids_from_distributions,
)
from dataset_profiler.profile_components.record_set.db.db_record_set import DBRecordSet
from dataset_profiler.profile_components.record_set.record_set_abc import (
    RecordSet,
)
from dataset_profiler.profile_components.record_set.record_set_extractor import (
    extract_record_sets_of_file_objects, extract_record_sets_of_file_sets,
)
from dataset_profiler.utilities import get_file_objects


class DatasetProfile:
    def __init__(self, dataset_specification: dict):
        self.dataset_specification = DatasetSpecification(dataset_specification)
        self.distribution_path = os.getenv("DATA_ROOT_PATH", "") + self.dataset_specification.dataPath

        self.file_objects, self.file_sets = get_file_objects(self.distribution_path)

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
        self.distributions: List[DistributionFileObject | DistributionFileSet] | None = None

        # RecordSet
        self.record_sets: List[RecordSet] | None = None

    def extract_distributions(
        self,
    ) -> List[DistributionFileObject | DistributionFileSet]:
        file_object_distributions = [
            get_distribution_of_file_object(
                self.distribution_path + file_object["path"], file_object["id"]
            )
            for file_object in self.file_objects
        ]
        file_sets_distributions = [
            get_distribution_of_file_set(
                self.distribution_path + file_set["path"], file_set["id"]
            )
            for file_set in self.file_sets
        ]

        return file_sets_distributions + file_object_distributions

    def extract_record_sets(self) -> List[RecordSet]:
        return (extract_record_sets_of_file_objects(self.file_objects, self.distribution_path) +
                extract_record_sets_of_file_sets(self.file_sets, self.distribution_path))

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

        db_ids_with_file_obj_ids = get_db_ids_from_distributions(
            profile_dict["distribution"]
        )
        for db_id, file_obj_id in db_ids_with_file_obj_ids:
            profile_dict["distribution"].extend(
                get_added_distributions(profile_dict["recordSet"], db_id, file_obj_id)
            )

        for record_set in self.record_sets:
            if record_set.inject_distribution:
                profile_dict["distribution"].append(record_set.inject_distribution)

        return profile_dict

    def to_json_str(self):
        return json.dumps(self.to_dict(), indent=3)
