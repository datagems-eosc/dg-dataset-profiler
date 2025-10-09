from pathlib import Path
from typing import List

from dataset_profiler.profile_components.record_set.csv.csv_record_set import (
    CSVRecordSet, get_record_sets_from_excel,
)
from dataset_profiler.profile_components.record_set.db.db_record_set import DBRecordSet
from dataset_profiler.profile_components.record_set.documents.document_record_set import FileType, DocumentRecordSet
from dataset_profiler.profile_components.record_set.documents.text.text_record_set import (
    TextRecordSet,
)
from dataset_profiler.profile_components.record_set.record_set_abc import (
    RecordSet,
)
from dataset_profiler.profile_components.record_set.documents.pdf.pdf_record_set import (
    PdfRecordSet,
)


def get_file_type(file_set, distribution_path) -> FileType | None:
    sample_file_suffix = next(Path(distribution_path + file_set["path"]).glob("*"), None).suffix.lower()
    match sample_file_suffix:
        case ".txt":
            return FileType.TEXT
        case ".pdf":
            return FileType.PDF
        case _:
            return None


def extract_record_sets_of_file_objects(file_objects, distribution_path) -> List[RecordSet]:
    record_sets = []
    for file_object in file_objects:
        file_extension = Path(file_object["path"]).suffix

        if file_extension == ".csv":
            csv_record_set = CSVRecordSet(
                distribution_path=distribution_path,
                file_object=file_object["path"],
                file_object_id=file_object["id"],
            )
            record_sets.append(csv_record_set)
        elif file_extension == ".db" or file_extension == ".sql":
            db_name_schema = file_object["path"].split("/")[-1].split(".")[-2]
            db_name, db_specific_schema = db_name_schema.split("-", 1)

            db_record_set = DBRecordSet(
                distribution_path=distribution_path,
                file_object=file_object["path"],
                file_object_id=file_object["id"],
                db_name=db_name,
                db_specific_schema=db_specific_schema,
            )
            record_sets.append(db_record_set)
        elif file_extension == ".xlsx":
            record_sets += get_record_sets_from_excel(distribution_path, file_object["path"], file_object["id"])

    return record_sets


def extract_record_sets_of_file_sets(file_sets: dict, distribution_path: str) -> List[RecordSet]:
    record_sets = []

    for file_set in file_sets:
        file_type = get_file_type(file_set, distribution_path)
        doc_record_set = DocumentRecordSet(distribution_path, file_set["path"],  file_set["id"], file_type)
        record_sets.append(doc_record_set)

    return record_sets
