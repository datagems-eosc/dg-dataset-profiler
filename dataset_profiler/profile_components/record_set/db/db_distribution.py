# DB Distribution is a special case of FileObject since it consists of multiple table that are contained in the relational db
# requiring multiple distributions
import uuid


def get_db_ids_from_distributions(distributions: list) -> list:
    ret_db_ids = []
    for distribution in distributions:
        if distribution["encodingFormat"] == "text/sql":
            ret_db_ids.append((distribution["name"], distribution["@id"]))
    return ret_db_ids


def get_added_distributions(record_sets: list, db_id, file_object_id) -> list:
    added_distributions = []
    for record_set in record_sets:
        if record_set["name"].split("/")[0] == db_id:
            record_set["name"] = record_set["name"].split("/")[-1]
            distribution_id = str(uuid.uuid4())
            added_distributions.append(
                {
                    "@type": "cr:FileObject",
                    "@id": distribution_id,
                    "name": record_set["name"],
                    "description": "",
                    "containedIn": {"@id": file_object_id},
                    "encodingFormat": "text/sql",
                }
            )

            for field in record_set["field"]:
                field["source"]["fileObject"]["@id"] = distribution_id

    return added_distributions
