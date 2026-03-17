import uuid
from typing import Union, Dict, List
from dataset_profiler.profile_components.record_set.record_set_abc import (
    RecordSet,
    TextChunk,
)

from dataset_profiler.profile_components.record_set.documents.text.text_utilities import (
    profile_text_file,
    chunk_text_by_paragraph,
    read_file_with_encoding,
    find_substring_positions,
    text_preprocess,
)
from dataset_profiler.profile_components.record_set.text.text_utilities import (
    get_keywords,
    get_summary,
)
from tqdm import tqdm
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

OLLAMA_API_BASE_URL = os.getenv("OLLAMA_API_BASE_URL", None)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", None)

# Default model for text processing using Scayle-LLM
SCAYLE_MODEL = "llama-3.3"


class TextRecordSet(RecordSet):
    def __init__(
        self,
        distribution_path: str,
        file_object: str,
        file_set_id: str,
        separator: Union[str, None] = None,
        header_index: int = 0,
        main_text_index: int = 1,
    ):
        super().__init__()
        self.distribution_path = distribution_path
        self.file_object = file_object
        self.separator = separator
        self.type = "dg:Document"
        self.name = file_object.split("/")[-1].split(".")[-2]
        self.id = str(uuid.uuid4())

        path_from_folder = "/".join(file_object.split("/")[-2:])
        self.content_url = f"s3://datagems/dataset_id/{path_from_folder}"

        # self.description = ""
        text_content, encoding = read_file_with_encoding(self.file_object)
        self.encoding = encoding
        # header, content = text_preprocess(
        #     text_content,
        #     separator=self.separator,
        #     header_index=header_index,
        #     main_text_index=main_text_index,
        # )
        # self.text = text_content
        # self.header = header
        # self.body = content

        # self.key = {"@id": self.name}
        profile = profile_text_file(file_object, separator=self.separator)

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
        self.summary = get_summary(
            text_content,
            model=SCAYLE_MODEL,
            max_words=800,
        )

        print("Generating keywords...")
        self.keywords = get_keywords(
            text_content,
            model=SCAYLE_MODEL,
            max_keywords_num=5,
        ).keywords

        self.source = {
            "fileSet": {"@id": file_set_id},
        }

    # TODO: extract_fields method is currently unused and references removed attributes/functions
    # This method would need to be refactored to work with current text extraction pipeline
    # def extract_fields(self):
    #     chunks = chunk_text_by_paragraph(self.text_content, chunk_size=300, chunk_overlap=20)
    #     model = OLLAMA_MODEL
    #     base_url = OLLAMA_API_BASE_URL
    #     fields = []
    #     print("\nExtracting fields...")
    #
    #     for chunk in tqdm(chunks):
    #         sos, pos = find_substring_positions(self.text_content, chunk)
    #         if sos and pos:
    #             keywords = get_keywords(chunk, model=SCAYLE_MODEL)
    #             temp = {
    #                 "text": chunk,
    #                 "sos": sos,
    #                 "eos": pos,
    #                 "references": [],
    #                 "keywords": keywords.keywords,
    #             }
    #             fields.append(ConcreteTextChunk(**temp))
    #         else:
    #             raise ValueError(f"Chunk '{chunk}' not found in the original text.")
    #     return fields

    def header_process(self):
        # extract metainfo from the header
        # @TODO:
        # Shall we use the regex or a general LLM prompt?
        pass

    def to_dict(self):
        return {
            "@type": self.type,
            "@id": self.id,
            "name": self.name,
            "contentUrl": self.content_url,
            "file_size_bytes": self.file_size_bytes,
            # "encoding": self.encoding,
            # "language": self.language,
            # "num_lines": self.num_lines,
            # "num_words": self.num_words,
            # "num_characters": self.num_characters,
            # "avg_sentence_length": self.avg_sentence_length,
            # "num_paragraphs": self.num_paragraphs,
            # "flesch_kincaid_grade": self.flesch_kincaid_grade,  # readability score
            "summary": self.summary,
            "keywords": self.keywords,
            "source": self.source,
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
            "sos": self.sos,
            "eos": self.eos,
            "references": self.references,
            "keywords": self.keywords,
        }
