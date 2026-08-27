CONTEXT_TEMPLATE = {
    "@language": "en",
    "@vocab": "https://schema.org/",
    # Instance identifiers are bare UUIDs, i.e. relative IRIs. Without a base
    # they resolve against the reading document's location.
    "@base": "https://datagems.eu/id/",
    "cr": "http://mlcommons.org/croissant/",
    "rai": "http://mlcommons.org/croissant/RAI/",
    "dg": "https://datagems.eu/ns/",
    "dct": "http://purl.org/dc/terms/",
    "data": {"@id": "cr:data", "@type": "@json"},
    "dataType": {"@id": "cr:dataType", "@type": "@vocab"},
    # NOT declared "@type": "@json": the value is already a json.dumps'd string,
    # and claiming JSON on top produced an rdf:JSON literal that parsed back to a
    # string rather than an object. Kept as a plain string literal, which is what
    # it actually is. "data" below is a real object, so it keeps @json.
    "examples": "cr:examples",
    # Carried as an opaque JSON literal: the block nests its own "summary",
    # "column" and "examples" keys, which would otherwise collide with the
    # record-set and Croissant terms of the same name defined below.
    "dataQuality": {"@id": "dg:hasDataQuality", "@type": "@json"},
}

# References Standard
REFERENCES_TEMPLATE = {
    "conformsTo": "dct:conformsTo",
    "citeAs": "cr:citeAs",
    "column": "cr:column",
    "extract": "cr:extract",
    "field": "cr:field",
    "fileProperty": "cr:fileProperty",
    "fileObject": "cr:fileObject",
    "fileSet": "cr:fileSet",
    "format": "cr:format",
    "includes": "cr:includes",
    "isLiveDataset": "cr:isLiveDataset",
    "jsonPath": "cr:jsonPath",
    "key": "cr:key",
    "md5": "cr:md5",
    "parentField": "cr:parentField",
    "path": "cr:path",
    "recordSet": "cr:recordSet",
    "references": "cr:references",
    "regex": "cr:regex",
    "repeated": "cr:repeated",
    "replace": "cr:replace",
    "sc": "https://schema.org/",
    "separator": "cr:separator",
    "source": "cr:source",
    "subField": "cr:subField",
    "transform": "cr:transform",
    "access": "dg:access",
    "uploadedBy": "dg:uploadedBy",
    "statistics": "dg:statistics",
    "semanticType": "dg:semanticType",
    "doi": "dg:doi",
    "fieldOfScience" : "dg:fieldOfScience",
    "status": "dg:status",
    "rowCount": "dg:rowCount",
    "mean": "dg:mean",
    "median": "dg:median",
    "standardDeviation": "dg:standardDeviation",
    "min": "dg:min",
    "max": "dg:max",
    "missingCount": "dg:missingCount",
    "missingPercentage": "dg:missingPercentage",
    "histogram": "dg:histogram",
    "uniqueCount": "dg:uniqueCount",
    "variance": "dg:variance",
    "range": "dg:range",
    "percentile05": "dg:percentile05",
    "percentile95": "dg:percentile95",
    "generatedAt": "dg:generatedAt",
    # Terms below were previously absent from the context. An unmapped key falls
    # through to "@vocab": "https://schema.org/", so each was expanding to a
    # schema.org IRI that does not exist (verified against the published
    # vocabulary). They are all declared in datagems-croissant-extension.ttl.
    # Only the IRI changes -- the JSON keys are untouched.
    "sample": "dg:sample",
    "country": "dg:country",
    "summary": "dg:summary",
    "numLines": "dg:numLines",
    "numWords": "dg:numWords",
    "numCharacters": "dg:numCharacters",
    "numParagraphs": "dg:numParagraphs",
    "avgSentenceLength": "dg:avgSentenceLength",
    "fleschKincaidGrade": "dg:fleschKincaidGrade",
    "pagesCount": "dg:pagesCount",
    "creationDate": "dg:creationDate",
    "modificationDate": "dg:modificationDate",
    "wd": "https://www.wikidata.org/wiki/",
    "containedIn": "cr:containedIn"
}
