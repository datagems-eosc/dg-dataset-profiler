# DB Distribution is a special case of FileObject since it consists of multiple table that are contained in the relational db
# requiring multiple distributions
def get_db_ids_from_distributions(distributions: list) -> list:
    ret_db_ids = []
    for distribution in distributions:
        if distribution["encodingFormat"] == "text/sql":
            ret_db_ids.append(distribution["name"])
    return ret_db_ids


def get_added_distributions(record_sets: list, db_id) -> list:
    added_distributions = []
    for record_set in record_sets:
        if record_set["key"]["@id"].split("/")[0] == db_id:
            added_distributions.append(
                {
                    "@type": "cr:FileObject",
                    "@id": record_set["key"]["@id"],
                    "containedIn": {"@id": record_set["key"]["@id"].split("/")[0]},
                    "encodingFormat": "text/sql",
                }
            )
    return added_distributions
