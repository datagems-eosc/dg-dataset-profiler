import json


class DatasetSpecification:
    """
    This class loads the dataset specification from a JSON file and stores the attributes as class variables.
    The JSON file is provided by the user adding a dataset
    """

    def __init__(self, specifications: dict):
        self.id = specifications["id"]

        self.name = specifications["name"]
        self.description = specifications["description"]
        self.citeAs = specifications["citeAs"]
        self.license = specifications["license"]
        self.url = specifications["url"]
        self.doi = specifications["doi"] if "doi" in specifications else ""

        # Datagems Specific Attributes
        self.headline = specifications["headline"]
        self.keywords = specifications["keywords"]
        self.fieldOfScience = specifications["fieldOfScience"]
        self.inLanguage = specifications["inLanguage"]
        self.country = specifications["country"]
        self.datePublished = specifications["datePublished"]
        self.dataPath = specifications["dataPath"]

        self.access = specifications["access"]
        self.uploadedBy = specifications["uploadedBy"]
