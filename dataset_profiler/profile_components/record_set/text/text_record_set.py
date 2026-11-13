import uuid
from pathlib import Path
from typing import Union, Dict, List
from dataset_profiler.profile_components.record_set.record_set_abc import (
    RecordSet,
    TextChunk,
)

from dataset_profiler.profile_components.record_set.text.text_utilities import (
    profile_text_file,
    read_file_with_encoding,
    text_preprocess,
)
from dataset_profiler.profile_components.record_set.document_description import (
    describe_document,
)
from dataset_profiler.profile_components.distribution import get_original_format


class TextRecordSet(RecordSet):
    def __init__(
        self,
        file_object: str,
        distribution_id: str,
        separator: Union[str, None] = None,
        header_index: int = 0,
        main_text_index: int = 1,
    ):
        super().__init__()
        self.file_object = file_object
        self.file_object_id = distribution_id
        self.separator = separator
        self.type = "cr:RecordSet"
        self.name = file_object.split(".")[-2]
        # self.description = ""
        text_content, encoding = read_file_with_encoding(
            self.file_object
        )
        self.encoding = encoding
        header, content = text_preprocess(
            text_content,
            separator=self.separator,
            header_index=header_index,
            main_text_index=main_text_index,
        )
        self.text = text_content
        self.header = header
        self.body = content

        self.key = {"@id": self.name}
        profile = profile_text_file(
            file_object, separator=self.separator
        )

        self.file_size_bytes = profile["file_size_bytes"]
        self.encoding = encoding
        self.language = profile["language"]
        self.num_lines = profile["num_lines"]
        self.num_words = profile["num_words"]
        self.num_characters = profile["num_characters"]
        self.avg_sentence_length = profile["avg_sentence_length"]
        self.num_paragraphs = profile["num_paragraphs"]
        self.flesch_kincaid_grade = profile["flesch_kincaid_grade"]
        description = describe_document(self.body, name=self.name)
        self.summary = description.summary
        self.keywords = description.keywords

        self.fields = self.extract_fields()

    def extract_fields(self):
        # CDD chunks the document itself from content.file_path.
        return []

    def header_process(self):
        # extract metainfo from the header
        # @TODO:
        # Shall we use the regex or a general LLM prompt?
        pass

    def to_dict(self):
        return {
            "@type": self.type,
            "@id": str(uuid.uuid4()),
            "name": self.name,
            "source": {
                "@type": "cr:FileObject",
                "@id": self.file_object_id,
            },
            "summary": self.summary,
            "keywords": self.keywords,
            # "file_size_bytes": self.file_size_bytes,
            # "encoding": self.encoding,
            "language": self.language,
            "numLines": self.num_lines,
            "numWords": self.num_words,
            "numCharacters": self.num_characters,
            "avgSentenceLength": self.avg_sentence_length,
            "numParagraphs": self.num_paragraphs,
            "fleschKincaidGrade": self.flesch_kincaid_grade,  # readability score
        }

    def to_dict_cdd(self):
        return {
            "file_object_id": self.file_object_id,
            "original_format": get_original_format(self.file_object),
            "source_file": self.file_object,
            "name": Path(self.name).name,
            "description": self.summary,
            "keywords": self.keywords,
            "content": {
                "type": "text",
                "file_path": self.file_object,
            },
        }


class ConcreteTextChunk(TextChunk):
    def __init__(self, text: str, sos: int, eos: int, references: List, keywords: List):
        super().__init__()
        self.sos = sos
        self.eos = eos
        self.text = text
        self.references = references
        self.keywords = keywords

    def to_dict(self) -> Dict:
        return {
            "@id": str(uuid.uuid4()),
            "@type": "dg:Chunk",
            "inFileId": "page:1",
            "dataType": "sc:Text",
            # "sos": self.sos,
            # "eos": self.eos,
            # "references": self.references,
            "keywords": self.keywords,
        }
