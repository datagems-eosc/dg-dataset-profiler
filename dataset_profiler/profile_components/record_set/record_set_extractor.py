from pathlib import Path
from typing import List

from dataset_profiler.profile_components.record_set.csv.csv_record_set import (
    CSVRecordSet,
)
from dataset_profiler.profile_components.record_set.db.db_record_set import DBRecordSet
from dataset_profiler.profile_components.record_set.text.text_record_set import (
    TextRecordSet,
)
from dataset_profiler.profile_components.record_set.record_set_abc import (
    RecordSet,
)
from dataset_profiler.profile_components.record_set.pdf.pdf_record_set import (
    PdfRecordSet,
)


def extract_record_sets(file_objects, distribution_path) -> List[RecordSet]:
    record_sets = []
    for file_object in file_objects:
        file_extension = Path(file_object).suffix

        if file_extension == ".csv":
            csv_record_set = CSVRecordSet(
                distribution_path=distribution_path, file_object=file_object
            )
            record_sets.append(csv_record_set)
        elif file_extension == ".db" or file_extension == ".sql":
            db_name = file_object.split("/")[-1].split(".")[-2]

            db_record_set = DBRecordSet(
                distribution_path=distribution_path,
                file_object=file_object,
                db_name=db_name,
                db_specific_schema=db_name,
            )
            record_sets.append(db_record_set)
        elif file_extension == ".txt":
            text_record_set = TextRecordSet(
                distribution_path=distribution_path, file_object=file_object
            )
            record_sets.append(text_record_set)
        elif file_extension == ".pdf":
            pdf_record_set = PdfRecordSet(
                distribution_path=distribution_path, file_object=file_object
            )
            record_sets.append(pdf_record_set)

    return record_sets
