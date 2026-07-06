from pathlib import Path
from typing import List

from dataset_profiler.profile_components.record_set.csv.csv_record_set import (
    CSVRecordSet, get_record_sets_from_excel,
)
from dataset_profiler.profile_components.record_set.db.db_record_set import DBRecordSet
from dataset_profiler.profile_components.record_set.documents.document_record_set import FileType, DocumentRecordSet
from dataset_profiler.profile_components.record_set.text.text_record_set import (
    TextRecordSet,
)
from dataset_profiler.profile_components.record_set.record_set_abc import (
    RecordSet,
)
from dataset_profiler.profile_components.record_set.pdf.pdf_record_set import (
    PdfRecordSet,
)
from dataset_profiler.configs.config_logging import logger


def get_file_type(file_set, distribution_path) -> FileType | None:
    sample_file = next(Path(distribution_path + file_set["path"]).glob("*"), None)
    if sample_file is None:
        return None
    sample_file_suffix = sample_file.suffix.lower()
    match sample_file_suffix:
        case ".txt":
            return FileType.TEXT
        case ".pdf":
            return FileType.PDF
        case _:
            return None


def extract_record_sets_of_file_objects(file_objects, distribution_path) -> List[RecordSet]:
    logger.info("Extracting record sets from file objects", num_file_objects=len(file_objects))
    record_sets = []
    for file_object in file_objects:
        file_extension = Path(file_object["path"]).suffix
        logger.debug("Processing file object", path=file_object["path"], file_extension=file_extension)

        if file_extension == ".csv":
            csv_record_set = CSVRecordSet(
                distribution_path=distribution_path,
                file_object=file_object["path"],
                file_object_id=file_object["id"],
            )
            record_sets.append(csv_record_set)
        # elif file_extension == ".pdf":
        #     pdf_record_set = PdfRecordSet(
        #         distribution_path=distribution_path,
        #         file_object=file_object,
        #     )
        #     record_sets.append(pdf_record_set)
        # elif file_extension == ".txt":
        #     text_record_set = TextRecordSet(
        #         distribution_path=distribution_path,
        #         file_object=file_object["path"],
        #     )
        #     record_sets.append(text_record_set)
        # elif file_extension == ".db" or file_extension == ".sql":
        #     db_name_schema = file_object["path"].split("/")[-1].split(".")[-2]
        #     db_name, db_specific_schema = db_name_schema.split("-", 1)
        #
        #     db_record_set = DBRecordSet(
        #         distribution_path=distribution_path,
        #         file_object=file_object["path"],
        #         file_object_id=file_object["id"],
        #         db_name=db_name,
        #         db_specific_schema=db_specific_schema,
        #     )
        #     record_sets.append(db_record_set)
        elif file_extension == ".xlsx":
            record_sets += get_record_sets_from_excel(distribution_path, file_object["path"], file_object["id"])

    logger.info("Extracted record sets from file objects", num_record_sets=len(record_sets))
    return record_sets


def extract_record_sets_of_database_connections(databases: list[dict], distributions:list) -> List[RecordSet]:
    logger.info("Extracting record sets from database connections", num_databases=len(databases))
    record_sets = []
    for database in databases:
        db_record_set = DBRecordSet(
            distribution_path="",
            file_object=database["file_object_id"],
            file_object_id=database["file_object_id"],
            db_name=database["database_name"],
            engine=database["engine"],
            db_specific_schema="public",
            distributions=distributions
        )
        record_sets.append(db_record_set)

    logger.info("Extracted record sets from database connections", num_record_sets=len(record_sets))
    return record_sets

def extract_record_sets_of_file_sets(file_sets: list, distribution_path: str) -> List[RecordSet]:
    logger.info("Extracting record sets from file sets", num_file_sets=len(file_sets))
    record_sets = []

    for file_set in file_sets:
        file_type = get_file_type(file_set, distribution_path)
        if file_type is not None:
            doc_record_set = DocumentRecordSet(distribution_path, file_set["path"],  file_set["id"], file_type)
            record_sets.append(doc_record_set)
        else:
            logger.warning("Skipping file set with no supported file type", path=file_set["path"])

    logger.info("Extracted record sets from file sets", num_record_sets=len(record_sets))
    return record_sets


def extract_record_sets_of_file_objects_in_file_sets(file_object_of_set_distributions, distribution_path) -> List[RecordSet]:
    logger.info("Extracting record sets from file objects in file sets",
                num_distributions=len(file_object_of_set_distributions))
    record_sets = []
    for distribution in file_object_of_set_distributions:
        file_extension = Path(distribution.content_url).suffix
        if file_extension == ".pdf":
            pdf_record_set = PdfRecordSet(
                file_object=distribution.content_url,
                distribution_id=distribution.id
            )
            record_sets.append(pdf_record_set)
        elif file_extension == ".txt":
            text_record_set = TextRecordSet(
                file_object=distribution.content_url,
                distribution_id=distribution.id
            )
            record_sets.append(text_record_set)

    logger.info("Extracted record sets from file objects in file sets", num_record_sets=len(record_sets))
    return record_sets
