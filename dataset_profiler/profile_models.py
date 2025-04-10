import json
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
    Distribution,
    get_distribution,
)
from dataset_profiler.profile_components.record_set.record_set_abc import (
    RecordSet,
)
from dataset_profiler.profile_components.record_set.record_set_extractor import (
    extract_record_sets,
)
from dataset_profiler.utilities import get_file_objects


class DatasetProfile:
    def __init__(self, dataset_specifications_path: str):
        self.dataset_specification = DatasetSpecification(dataset_specifications_path)
        self.distribution_path = self.dataset_specification.dataPath

        self.file_objects, self.file_sets = get_file_objects(self.distribution_path)

        self.dataset_top_level = DatasetTopLevel(
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
        )

        # Distribution
        self.distributions: List[Distribution] = self.extract_distributions()

        # RecordSet
        self.record_sets: List[RecordSet] = self.extract_record_sets()

    def extract_distributions(self) -> List[Distribution]:
        return [
            get_distribution(self.distribution_path + file_object)
            for file_object in self.file_objects
        ]

    def extract_record_sets(self) -> List[RecordSet]:
        return extract_record_sets(self.file_objects, self.distribution_path)

    def to_dict(self):
        profile_dict = {
            "@context": {**CONTEXT_TEMPLATE, **REFERENCES_TEMPLATE},
            **self.dataset_top_level.to_dict(),
            "distribution": [
                distribution.to_dict() for distribution in self.distributions
            ],
            "recordSet": [record_set.to_dict() for record_set in self.record_sets],
        }

        return profile_dict

    def to_json_str(self):
        return json.dumps(self.to_dict(), indent=3)
