import argparse
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
from litellm.types.utils import ModelResponse, Choices, Message, Usage

from dotenv import load_dotenv

load_dotenv()

import pandas as pd
from tqdm import tqdm

# from components.darelabdb.nlp_llm.bedrock import BedrockLLM
from dataset_profiler.common_llm import CommonLLMConnector
# from components.darelabdb.nlp_llm.ollama import OllamaLLM
from dataset_profiler.profile_components.record_set.db.database_connector import (
    DatagemsPostgres,
)
# from development.datagems_profiler.cta.benchmarks.benchmarks import T2Dv2Benchmark
# from development.datagems_profiler.cta.cta_evaluation import evaluate_with_similarity

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class ColumnTypeAnnotator:
    def __init__(
        self,
        model: str = "eu.anthropic.claude-sonnet-4-6", # Temporarily use only one model from Bedrock until SCALY LLMs are ready to use
        sample_size: int = 10,
        llm_provider: str = "bedrock",
    ):
        self.sample_size = sample_size
        self.model_name = model
        self.llm_provider = llm_provider

        if self.llm_provider == "bedrock":
            self.llm = CommonLLMConnector(
                provider="bedrock",
                model="eu.anthropic.claude-sonnet-4-6",
                config_file="dataset_profiler/common_llm/configs/llm_config.yaml")
        else:
            raise ValueError(
                f"Unsupported llm_provider: {llm_provider}. Use 'bedrock' or '...'."
            )

        self.system_message = self._get_system_message()

    @staticmethod
    def _get_system_message() -> str:
        return (
            "You are an expert Data Analyst specializing in Semantic Data Profiling. "
            "Your task is Column Type Annotation.\n\n"
            "GUIDELINES:\n"
            "1. Return your answer in 1 to max 3 words.\n"
            "2. Do NOT return structural data types (e.g., 'string', 'float').\n"
            "3. Be as exact and precise as possible.\n"
            "4. If the target column header best describes the column content, return that.\n"
            "5. If unknown, return: unknown\n"
            "6. No punctuation, quotes, or explanations.\n"
            "7. If the target column contains mostly unique identifiers, return 'identifier'.\n"
        )

    def _build_prompt(
        self,
        col: str,
        all_headers: List[str],
        samples: List[Any],
        semantic_types: Dict[str, str],
        extra_info: Optional[Sequence[Dict[str, Any]]] = None,
        labels: Optional[List[str]] = None,
    ) -> str:
        context_cols = [c for c in all_headers if c != col]
        prompt = f"<target_column_header>{col}</target_column_header>\n"
        prompt += f"<rest_headers>{context_cols}</rest_headers>\n"
        prompt += f"<sample_values>{samples}</sample_values>\n"
        if semantic_types:
            prompt += f"<previous_annotations>{semantic_types}</previous_annotations>\n"
        if extra_info is not None:
            prompt += f"<extra_info>{extra_info}</extra_info>\n"

        if labels and len(labels) > 0:
            prompt += f"<labels>{labels}</labels>\n"
            prompt += "The possible semantic types are listed in <labels>. Classify the target column into one of these types if possible. If it doesn't fit any, return 'unknown'.\n"
        else:
            prompt += "\nBased on the context columns and the sample values, what is the semantic type of the target column?\n"

        prompt += "Return your answer immediately after ANSWER:"

        return prompt

    def _parse_response(self, response: str) -> str:
        try:
            content = response.choices[0].message.content
            if "ANSWER:" in content:
                return content.split("ANSWER:", 1)[1].strip().lower()
            return content.strip().lower()
        except Exception as e:
            logger.warning(f"Failed to parse response: {e}")
            return "unknown"

    def annotate_columns(
        self,
        df: Optional[pd.DataFrame] = None,
        db: Optional[DatagemsPostgres] = None,
        table_name: Optional[str] = None,
        columns_to_annotate: Optional[List[str]] = None,
        extra_info_df: Optional[pd.DataFrame] = None,
        show_progress: bool = False,
        labels: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """Annotates all columns either of a DataFrame or of a specific table of a Database"""

        # In case of database columns annotation, fetch a subtable (100 first rows) of the target table
        if df is None:
            if db is None or table_name is None:
                raise ValueError("Either df or both db and table_name must be provided")
            try:
                query = f"SELECT * FROM {table_name} LIMIT 100;"
                result = db.execute(query)
                df = (
                    result if isinstance(result, pd.DataFrame) else pd.DataFrame(result)
                )
                df.to_csv(
                    f"debugging_era5land.csv",
                    index=False,
                )  # Save for debugging
            except Exception as e:
                logger.error(f"Failed to annotate columns from database: {e}")
                return {col: "error" for col in (columns_to_annotate or [])}

        all_headers = df.columns.tolist()
        target_cols = [
            c for c in (columns_to_annotate or all_headers) if c in all_headers
        ]

        semantic_types = {}
        pbar = tqdm(
            target_cols,
            desc="Annotating columns",
            unit="col",
            disable=not show_progress,
        )

        for col in pbar:
            if show_progress:
                pbar.set_description(f"Annotating: '{col}'")

            valid_data = df[col].dropna()
            samples = (
                valid_data.sample(min(self.sample_size, len(valid_data))).tolist()
                if not valid_data.empty
                else []
            )
            extra_info = (
                extra_info_df.to_dict(orient="records")
                if extra_info_df is not None
                else None
            )

            messages = [
                {"role": "system", "content": self.system_message},
                {
                    "role": "user",
                    "content": self._build_prompt(
                        col, all_headers, samples, semantic_types, extra_info, labels
                    ),
                },
            ]

            try:
                raw_response = self.llm.chat(messages, stream=False)
                print("RAW_RESPONSE:", raw_response)
                semantic_types[col] = self._parse_response(raw_response)
            except Exception as e:
                logger.error(f"Error for column '{col}': {e}")
                semantic_types[col] = "error"

        return semantic_types


def save_results(data: List[Dict], prefix: str, model_name: str) -> Path:
    """Helper to save results to a CSV file in a 'results' directory."""
    output_dir = Path("cta_results")
    output_dir.mkdir(exist_ok=True, parents=True)

    clean_model = model_name.replace(":", "-").replace("/", "-")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = output_dir / f"{prefix}_{clean_model}_{timestamp}.csv"

    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    logger.info(f"Results saved to {filename}")

    return filename

def annotate_database(args, profiler: ColumnTypeAnnotator):
    logger.info("Database mode selected.")

    db = DatagemsPostgres(database=args.file, schema="public", engine="PostgreSQL")
    tables_columns = db.get_tables_and_columns()

    for table_name in tables_columns["tables"]:
        logger.info(f"Annotating table: {table_name}")
        results = profiler.annotate_columns(
            db=db, table_name=table_name, show_progress=True
        )
        save_results(
            [{"column": k, "predicted_type": v} for k, v in results.items()],
            f"db_{table_name}",
            profiler.model_name,
        )

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", help="Path to CSV file")
    parser.add_argument(
        "-db",
        "--database",
        action="store_true",
        help="Whether to run in database mode",
    )
    parser.add_argument("-sp", "--sep", default=",", help="CSV separator")
    parser.add_argument(
        "-e",
        "--encoding",
        default="utf-8",
        help="CSV encoding (default is 'utf-8'). Choose between [utf-8, cp1252]",
    )
    parser.add_argument(
        "--extra_info", action="store_true", help="Path to extra info CSV (optional)"
    )
    parser.add_argument(
        "--output_filename",
        default="file",
        help="Prefix for output filename (default: 'file')",
    )

    args = parser.parse_args()

    annotator = ColumnTypeAnnotator(
        sample_size=10,
    )

    # if args.file and not args.database:
    #     print(annotator(df=annotator, args))
    # elif args.database:
    #     annotate_database(args, annotator)
    # else:
    #     logger.error("Please provide -f (file) or -b (benchmark).")
