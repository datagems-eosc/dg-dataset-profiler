from dataset_profiler.profile_components.record_set.pdf.pdf_record_set import (
    PdfRecordSet,
)
import json
from pathlib import Path

curr_path = Path(__file__).parent.resolve()

if __name__ == "__main__":
    # Example usage
    distribution_path = "tests/assets/pdf/data/"
    file_object = "960.pdf"

    pdf_record_set = PdfRecordSet(distribution_path, file_object)
    # print the profile of the text record set in dict format with indentation
    print(json.dumps(pdf_record_set.to_dict(), indent=4, ensure_ascii=False))
