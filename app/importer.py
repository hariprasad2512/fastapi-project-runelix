import logging
import re
from dataclasses import dataclass
from io import BytesIO
from typing import Any

import pandas as pd


logger = logging.getLogger(__name__)
MANDATORY_COLUMNS = (
    "Product Name",
    "Category",
    "Price",
    "Quantity",
    "Supplier Name",
    "Supplier Email",
)
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@dataclass
class ImportResult:
    valid_records: list[dict[str, Any]]
    skipped_records: list[dict[str, Any]]


def is_valid_email(value: str) -> bool:
    return bool(EMAIL_PATTERN.fullmatch(value))


def is_valid_number(value: str) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return pd.notna(number) and number not in (float("inf"), float("-inf")) and number >= 0


def clean_dataframe(dataframe: pd.DataFrame) -> ImportResult:
    missing_columns = [column for column in MANDATORY_COLUMNS if column not in dataframe.columns]
    if missing_columns:
        raise ValueError(f"Input file is missing required columns: {missing_columns}")

    valid_records = []
    skipped_records = []
    for index, row in dataframe.iterrows():
        record = {column: str(row[column]).strip() for column in MANDATORY_COLUMNS}
        reasons = []
        missing_fields = [column for column, value in record.items() if not value]
        if missing_fields:
            reasons.append(f"missing mandatory fields: {missing_fields}")
        else:
            if not is_valid_email(record["Supplier Email"]):
                reasons.append("invalid Supplier Email format")
            invalid_numeric_fields = [
                column for column in ("Price", "Quantity")
                if not is_valid_number(record[column])
            ]
            if invalid_numeric_fields:
                reasons.append(f"invalid numeric value(s): {invalid_numeric_fields}")

        if reasons:
            skipped = {"row": index + 2, "reasons": reasons}
            skipped_records.append(skipped)
            logger.warning("Skipping row %s: %s", skipped["row"], "; ".join(reasons))
        else:
            valid_records.append(record)

    return ImportResult(valid_records, skipped_records)


def clean_xlsx(file_bytes: bytes) -> ImportResult:
    dataframe = pd.read_excel(BytesIO(file_bytes), dtype=str, keep_default_na=False)
    return clean_dataframe(dataframe)
