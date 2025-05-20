from dataset_profiler.profile_components.record_set.text.text_record_set import (
    TextRecordSet,
)
import json
from pathlib import Path

curr_path = Path(__file__).parent.resolve()

if __name__ == "__main__":
    # Example usage
    distribution_path = "tests/assets/britannica_text/data/kp-editions/eb07/TXT_v1/a2/"
    file_object = "kp-eb0702-001306-9978-v1.txt"
    separator = (
        "+=====================================================================+"
    )
    header_index = 0
    main_text_index = 1

    text_record_set = TextRecordSet(
        distribution_path, file_object, separator, header_index, main_text_index
    )

    # print the profile of the text record set in dict format with indentation
    print("Text Record Set Profile:")
    print("=====================================")
    print(f"Name: {text_record_set.name}")
    print(f"Type: {text_record_set.type}")
    print(f"File Size (bytes): {text_record_set.file_size_bytes}")
    print(f"Encoding: {text_record_set.encoding}")
    print(f"Language: {text_record_set.language}")
    print(f"Number of Lines: {text_record_set.num_lines}")
    print(f"Number of Words: {text_record_set.num_words}")
    print(f"Number of Characters: {text_record_set.num_characters}")
    print(f"Average Sentence Length: {text_record_set.avg_sentence_length}")
    print(f"Number of Paragraphs: {text_record_set.num_paragraphs}")
    print(f"Flesch-Kincaid Grade: {text_record_set.flesch_kincaid_grade}")
    print(f"Summary: {text_record_set.summary}")
    print(f"Chunks: {len(text_record_set.fields)}")
    print("=====================================")
    print("Field Details:")
    for chunk in text_record_set.fields:
        print(f" - sos: {chunk.sos}")
        print(f" - eos: {chunk.eos}")
        print(f" - text: {chunk.text}")
        print(f" - keywords: {chunk.keywords}")
        print(f" - references: {chunk.references}")
        print("=====================================")

    # save to json
    # output_file = curr_path / "sample_text_record_set.json"
    # with open(output_file, "w") as f:
    #    json.dump(text_record_set.to_dict(), f, indent=4)

    # print json
    print(json.dumps(text_record_set.to_dict(), indent=4))
