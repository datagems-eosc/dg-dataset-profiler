"""What the semantic type annotator shows the model for a database table."""

import pandas as pd
from litellm.types.utils import Choices, Message, ModelResponse

from dataset_profiler.profile_components.cta import ColumnTypeAnnotator

# Taken at import, before conftest stubs annotate_columns on the class for each test.
ANNOTATE_COLUMNS = ColumnTypeAnnotator.annotate_columns


class FakeDB:
    def __init__(self, df):
        self.df = df

    def execute(self, query):
        return self.df


class RecordingLLM:
    def __init__(self):
        self.prompts = []

    def chat(self, messages, stream=False):
        self.prompts.append(messages[-1]["content"])
        return ModelResponse(choices=[Choices(message=Message(content="ANSWER: total precipitation"))])


def annotator():
    a = object.__new__(ColumnTypeAnnotator)
    a.sample_size, a.model_name, a.llm_provider = 10, "fake", "fake"
    a.system_message = ColumnTypeAnnotator._get_system_message()
    a.llm = RecordingLLM()
    return a


def test_database_prompt_names_the_table_and_dataset():
    a = annotator()
    df = pd.DataFrame({"tp": [0.001, 0.002], "latitude": [45.0, 45.1]})
    context = pd.DataFrame([{"dataset": "Era5land", "description": "ERA5-Land reanalysis"}])
    ANNOTATE_COLUMNS(a, db=FakeDB(df), table_name="meteo_tp", columns_to_annotate=["tp"], extra_info_df=context)
    prompt = a.llm.prompts[0]
    assert "<table_name>meteo_tp</table_name>" in prompt
    assert "ERA5-Land reanalysis" in prompt


def test_file_prompt_has_no_table_name():
    a = annotator()
    ANNOTATE_COLUMNS(a, df=pd.DataFrame({"tp": [0.001, 0.002]}))
    assert "<table_name>" not in a.llm.prompts[0]


def test_fill_values_are_not_shown_as_samples():
    a = annotator()
    df = pd.DataFrame({"tp": [-9e33] * 50 + [0.001] * 5})
    ANNOTATE_COLUMNS(a, df=df)
    samples = a.llm.prompts[0].split("<sample_values>")[1].split("</sample_values>")[0]
    assert "e+33" not in samples
    assert "0.001" in samples
