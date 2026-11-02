import os
from collections import Counter
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
from dataset_profiler.profile_components.record_set.json.json_record_set import (
    JSONRecordSet,
    is_json_file,
)
from dataset_profiler.configs.config_logging import logger

# JSON files in one folder that get the LLM enrichments (semantic types and a
# summary). A folder of thousands of one-record files would otherwise cost
# thousands of LLM calls; the files past the cap are still fully profiled.
DEFAULT_JSON_LLM_MAX_FILES_PER_FOLDER = 20


def _json_llm_max_files_per_folder() -> int:
    return int(os.environ.get("JSON_LLM_MAX_FILES_PER_FOLDER",
                              DEFAULT_JSON_LLM_MAX_FILES_PER_FOLDER))


def _json_record_set(file_path: str, file_object_id: str, use_llm: bool = True):
    """A JSON record set, or None when the file cannot be profiled at all.

    Invalid JSON is handled inside JSONRecordSet (it yields a record set with
    parse_errors set); this only guards against the unexpected, so one bad file
    never fails the dataset.
    """
    try:
        return JSONRecordSet(file_path, file_object_id, use_llm=use_llm)
    except Exception as e:  # noqa: BLE001 - logged; the file stays in the distribution
        logger.exception("Failed to profile JSON file, skipping its record set",
                         file=file_path, error=str(e))
        return None


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
        elif file_extension in (".pdf", ".txt"):
            # Same path the distribution was built from, so the CDD profile can match them by id.
            # A document that fails to parse keeps its bare distribution entry instead of failing the job.
            document_record_set_class = PdfRecordSet if file_extension == ".pdf" else TextRecordSet
            try:
                record_sets.append(document_record_set_class(
                    file_object=distribution_path + file_object["path"],
                    distribution_id=file_object["id"],
                ))
            except Exception as e:
                logger.warning("Failed to process document file object, skipping",
                               path=file_object["path"], error=str(e))
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
        elif is_json_file(file_object["path"]):
            json_record_set = _json_record_set(
                os.path.join(distribution_path, file_object["path"]), file_object["id"]
            )
            if json_record_set is not None:
                record_sets.append(json_record_set)

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
    json_files_per_folder: Counter = Counter()
    for distribution in file_object_of_set_distributions:
        file_extension = Path(distribution.content_url).suffix
        if is_json_file(distribution.content_url):
            json_files_per_folder[distribution.contained_in] += 1
            seen = json_files_per_folder[distribution.contained_in]
            use_llm = seen <= _json_llm_max_files_per_folder()
            if seen == _json_llm_max_files_per_folder() + 1:
                logger.info("JSON files past the per-folder cap are profiled without LLM enrichments",
                            folder=Path(distribution.content_url).parent.name,
                            cap=_json_llm_max_files_per_folder())
            json_record_set = _json_record_set(distribution.content_url, distribution.id,
                                               use_llm=use_llm)
            if json_record_set is not None:
                record_sets.append(json_record_set)
            continue
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
