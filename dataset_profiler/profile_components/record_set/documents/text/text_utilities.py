import os
import re
import chardet
import nltk
import string
from typing import List
from collections import Counter
from langdetect import detect_langs
from nltk.corpus import stopwords
from pydantic import BaseModel
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langsmith import traceable
from dotenv import load_dotenv, find_dotenv

nltk.download("stopwords")
load_dotenv(find_dotenv())


# Define stop words
# use stop words from nltk


STOP_WORDS = set(stopwords.words("english"))
# or define your own stop words
# STOP_WORDS = set(["the", "and", "is", "in", "to", "of", "a", "for", "on", "with"])


def count_syllables(word):
    """
    Count the number of syllables in a word.
    Args:
        word (str): Input word.
    Returns:
        int: Number of syllables in the word.
    """
    vowels = "aeiouy"
    return sum(1 for char in word.lower() if char in vowels)


def read_file_with_encoding(file_path):
    """
    Read a file with the detected encoding.
    Args:
        file_path (str): Path to the file.
    Returns:
        tuple: A tuple containing the text and the detected encoding.
    """
    with open(file_path, "rb") as f:
        raw_data = f.read()
        encoding = chardet.detect(raw_data)["encoding"]
        if encoding is None:
            encoding = "utf-8"
        text = raw_data.decode(encoding)
    return text, encoding


def detect_language(text):
    """
    Detect the language of the text using langdetect.
    Args:
        text (str): Input text.
    Returns:
        str: Detected language code (e.g., 'en' for English).
    """
    language = "n/a"
    try:
        language = detect_langs(text)[0].lang
    except Exception:
        pass
    return language


def compute_basic_stats(text):
    """
    Compute basic statistics for the text.
    Args:
        text (str): Input text.
    Returns:
        tuple: A tuple containing the number of lines, words, characters, and word counts.
    """
    lines = text.splitlines()
    num_lines = len(lines)
    num_characters = len(text)
    words = re.findall(r"\b\w+\b", text.lower())
    num_words = len(words)
    word_counts = Counter(words)
    return num_lines, num_words, num_characters, word_counts


def compute_word_stats(word_counts, num_words, stop_words):
    """
    Compute word-level statistics for the text.
    Args:
        word_counts (Counter): A Counter object containing word counts.
        num_words (int): Total number of words in the text.
        stop_words (set): A set of stop words.
    Returns:
        dict: A dictionary containing word-level statistics.
    """
    total_word_length = sum(len(word) * count for word, count in word_counts.items())
    avg_word_length = total_word_length / num_words if num_words > 0 else 0
    unique_words = len(word_counts)
    most_common_words = word_counts.most_common(5)
    typological_diversity = unique_words / num_words if num_words > 0 else 0
    content_word_counts = sum(
        count for word, count in word_counts.items() if len(word) > 3
    )
    lexical_density = content_word_counts / num_words if num_words > 0 else 0
    longest_word = max(word_counts, key=len) if word_counts else ""
    shortest_word = min(word_counts, key=len) if word_counts else ""
    num_stop_words = sum(
        word_counts[word] for word in stop_words if word in word_counts
    )
    return {
        "avg_word_length": avg_word_length,
        "unique_words": unique_words,
        "most_common_words": most_common_words,
        "typological_diversity": typological_diversity,
        "lexical_density": lexical_density,
        "longest_word": longest_word,
        "shortest_word": shortest_word,
        "num_stop_words": num_stop_words,
    }


def compute_sentence_stats(text: str) -> tuple:
    """
    Compute sentence-level statistics for the text.
    Args:
        text (str): Input text.
    Returns:
        tuple: A tuple containing the number of sentences and average sentence length.
    """
    sentences = re.split(r"[.!?]", text)
    sentence_lengths = [
        len(re.findall(r"\b\w+\b", sentence))
        for sentence in sentences
        if sentence.strip()
    ]
    num_sentences = len(sentence_lengths)
    avg_sentence_length = (
        sum(sentence_lengths) / num_sentences if num_sentences > 0 else 0
    )
    return num_sentences, avg_sentence_length


def compute_character_stats(text) -> dict:
    """
    Compute character-level statistics for the text.
    Args:
        text (str): Input text.
    Returns:
        dict: A dictionary containing character-level statistics.
    """
    num_characters = len(text)
    punctuation_count = sum(1 for char in text if char in string.punctuation)
    capital_letters = sum(1 for char in text if char.isupper())
    digit_count = sum(1 for char in text if char.isdigit())
    whitespace_count = sum(1 for char in text if char.isspace())
    return {
        "punctuation_frequency": (
            punctuation_count / num_characters if num_characters > 0 else 0
        ),
        "capitalization_ratio": (
            capital_letters / num_characters if num_characters > 0 else 0
        ),
        "digit_frequency": digit_count / num_characters if num_characters > 0 else 0,
        "whitespace_ratio": (
            whitespace_count / num_characters if num_characters > 0 else 0
        ),
    }


def profile_text_file(file_path, separator, chunk_size=300, chunk_overlap=20) -> dict:
    """
    Profile a text file and return its statistics.
    Args:
        file_path (str): Path to the text file.
        separator (str): Separator string that divides header and main_text.
        chunk_size (int): Maximum size of each chunk in characters.
        chunk_overlap (int): Number of overlapping characters between chunks.
    Returns:
        dict: A dictionary containing various statistics about the text file.
    """
    try:
        # 1. get general file information
        file_size = os.path.getsize(file_path)
        text, encoding = read_file_with_encoding(file_path)
        language = detect_language(text)
        num_lines, num_words, num_characters, word_counts = compute_basic_stats(text)
        word_stats = compute_word_stats(word_counts, num_words, STOP_WORDS)
        num_sentences, avg_sentence_length = compute_sentence_stats(text)
        char_stats = compute_character_stats(text)
        total_syllables = sum(
            count_syllables(word) * count for word, count in word_counts.items()
        )
        if num_words > 0 and num_sentences > 0:
            fk_grade = (
                0.39 * (num_words / num_sentences)
                + 11.8 * (total_syllables / num_words)
                - 15.59
            )
        else:
            fk_grade = 0
        paragraphs = text.split("\n\n")
        num_paragraphs = len(paragraphs)
        res = {
            "file_size_bytes": file_size,
            "encoding": encoding,
            "language": language,
            "num_lines": num_lines,
            "num_words": num_words,
            "num_characters": num_characters,
            **word_stats,
            "avg_sentence_length": avg_sentence_length,
            "num_paragraphs": num_paragraphs,
            "flesch_kincaid_grade": fk_grade,
            **char_stats,
        }
        return res
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except UnicodeDecodeError:
        raise Exception(f"Could not decode file {file_path} with detected encoding.")
    except Exception as e:
        raise Exception(f"Error processing file {file_path}: {e}")


def chunk_text_by_paragraph(
    text, chunk_size=300, chunk_overlap=20, chunk_separator=["\n\n", "\n", ". "]
) -> list:
    """
    Chunk text into natural paragraphs using LangChain's RecursiveCharacterTextSplitter.

    Args:
        text (str): Input text to be chunked
        chunk_size (int): Maximum size of each chunk in characters
        chunk_overlap (int): Number of overlapping characters between chunks

    Returns:
        list: List of chunked text segments
    """
    # Initialize the text splitter with paragraph-focused separators
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=chunk_separator,  # Only split at paragraph breaks
        length_function=len,
        keep_separator=False,  # Retain paragraph breaks in output
        is_separator_regex=False,
    )

    # Split the text into chunks
    chunks = text_splitter.split_text(text)
    return chunks


def find_substring_positions(text, substring) -> tuple:
    """
    Find the start and end positions of a substring in the given text.
    Returns tuple (start_pos, end_pos) or None if substring is not found.
    """
    start_pos = text.find(substring)

    if start_pos == -1:  # Substring not found
        return (None, None)

    end_pos = start_pos + len(substring) - 1
    return (start_pos, end_pos)


def get_chunks_with_positions(text, chunk_size=300, chunk_overlap=20) -> list:
    """
    Get chunks of text with their start and end positions in the original text.
    """
    chunks = chunk_text_by_paragraph(text, chunk_size, chunk_overlap)
    positions = []

    for chunk in chunks:
        pos = find_substring_positions(text, chunk)
        if pos:
            positions.append((chunk, pos))

    return positions


def text_preprocess(
    text, separator, header_index=0, main_text_index=1
) -> tuple:  # for our sample header_index=0, main_text_index=1
    """
    Splits input text into header and main_text based on the separator.

    Args:
        text (str): Input text to be split.
        separator (str): Separator string that divides header and main_text.

    Returns:
        tuple: (header, main_text) where header is the text before the separator
        and main_text is the text after the separator. Returns (None, str)
        if separator is not found.
    """
    if separator not in text:
        return None, text.strip()

    # Split the text at the first occurrence of the separator
    parts = text.split(separator)
    # filter the parts if parts.strip() is empty
    parts = [part for part in parts if part.strip() and len(part.strip()) > 0]
    # Extract header (before separator) and main_text (after separator)
    header = parts[header_index].strip()
    main_text = parts[main_text_index].strip() if len(parts) > 1 else ""

    return header, main_text


# AI based information  retrieval
class KeyWords(BaseModel):
    """
    A class to represent keywords extracted from text.
    """

    keywords: List[str]


class TextSummary(BaseModel):
    """
    A class to represent a summary of text.
    """

    summary: str


@traceable(
    tags=["keyword_extraction"], name="get_keywords_ollama", project_name="TextProfiler"
)
def get_keywords_ollama(
    text: str, model, base_url, max_keywords_num: int = 3
) -> KeyWords:
    """
    Extract keywords from text using ChatOllama.

    Args:
        text (str): The input text to extract keywords from.
        max_keywords_num (int): The maximum number of keywords to return.

    Returns:
        KeyWords: A KeyWords object containing the list of extracted keywords.
    """
    try:
        # Initialize the ChatOllama model
        llm = ChatOllama(model=model, temperature=0, base_url=base_url)

        # Define the prompt template
        prompt = ChatPromptTemplate.from_template(
            """Extract up to {max_keywords_num} keywords from the following text.
            Return the keywords as a list of strings, ensuring they are concise and relevant to the main topics or entities in the text.

            Text: {text}

            Output format:
            ```json
            {{
                "keywords": ["keyword1", "keyword2", ...]
            }}
            ```"""
        )

        # Create a chain with structured output
        chain = prompt | llm.with_structured_output(KeyWords)

        # Run the chain with the input parameters
        result = chain.invoke({"text": text, "max_keywords_num": max_keywords_num})

        # Ensure the result is always a KeyWords instance
        if isinstance(result, KeyWords):
            return result
        elif isinstance(result, dict):
            return KeyWords(**result)
        else:
            raise TypeError("Unexpected result type from chain.invoke")
    except Exception as e:
        print(f"Error in get_keywords_ollama: {e}")
        return KeyWords(keywords=[])


@traceable(
    tags=["summarization"], name="get_summary_ollama", project_name="TextProfiler"
)
def get_summary_ollama(text: str, model, base_url, max_words: int = 600) -> str:
    """
    Get a description of the text using ChatOllama.

    Args:
        text (str): The input text to describe.

    Returns:
        str: A concise summary of the text.
    """
    try:
        # Initialize the ChatOllama model
        llm = ChatOllama(model=model, temperature=0, base_url=base_url)

        # Define the prompt template
        prompt = ChatPromptTemplate.from_template(
            """Generate a concise summary of the following text.
            The summary should be no more than {max_words} words and should capture the main ideas and themes of the text.

            Text: {text}

            Output format:
            ```json
            {{
                "summary": "Your summary here"
            }}
            ```"""
        )

        # Create a chain with structured output
        chain = prompt | llm.with_structured_output(TextSummary)

        # Run the chain with the input parameters
        result = chain.invoke({"text": text, "max_words": max_words})

        if isinstance(result, TextSummary):
            return result.summary
        elif isinstance(result, dict):
            return TextSummary(**result).summary
        else:
            raise TypeError(
                f"Unexpected result type from chain.invoke, {type(result)} | {result}"
            )
    except Exception as e:  # with errors output empty string
        print(f"Error in get_summary_ollama: {e}")
        return ""
