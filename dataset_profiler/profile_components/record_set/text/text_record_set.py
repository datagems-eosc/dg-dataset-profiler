import uuid
from typing import Union, Dict, List
from dataset_profiler.profile_components.record_set.record_set_abc import (
    RecordSet,
    TextChunk,
)

from dataset_profiler.profile_components.record_set.text.text_utilities import (
    profile_text_file,
    chunk_text_by_paragraph,
    read_file_with_encoding,
    find_substring_positions,
    text_preprocess,
    get_keywords,
    get_summary,
)
from tqdm import tqdm

# Default model for text processing using Scayle-LLM
SCAYLE_MODEL = "llama-3.3"


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
        print("\nGenerating summary...")

        # self.summary = get_summary(
        #     self.body,
        #     model=SCAYLE_MODEL,
        # )
        #
        # print("Generating keywords...")
        # self.keywords = get_keywords(
        #     self.body,
        #     model=SCAYLE_MODEL,
        #     max_keywords_num=5,
        # ).keywords
        self.summary = ""
        self.keywords = []

        self.fields = self.extract_fields()

    def extract_fields(self):
        # text_object = open(self.distribution_path + self.file_object, "r")
        # text_content = text_object.read()
        # text_object.close()
        chunks = chunk_text_by_paragraph(self.body, chunk_size=300, chunk_overlap=20)
        model = SCAYLE_MODEL
        fields = []
        print("\nExtracting fields...")

        for chunk in tqdm(chunks):
            sos, pos = find_substring_positions(self.text, chunk)
            if sos is not None and pos is not None:
                # keywords = get_keywords(chunk, model)
                temp = {
                    "text": chunk,
                    "sos": sos,
                    "eos": pos,
                    "references": [],
                    "keywords": [],
                }
                fields.append(ConcreteTextChunk(**temp))
            else:
                raise ValueError(f"Chunk '{chunk}' not found in the original text.")
        return fields

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
            "field": [chunk.to_dict() for chunk in self.fields],
        }

    def to_dict_cdd(self):
        return {
            "file_object_id": self.file_object_id,
            "original_format": "text",
            "source_file": self.file_object,
            "name": self.name,
            "description": self.summary,
            "keywords": self.keywords,
            "chunked_content": [
                {
                    "section": "",
                    "subsection": "",
                    "chunks": [chunk.text for chunk in self.fields],
                }
            ],
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
