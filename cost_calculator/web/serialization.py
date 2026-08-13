"""Serialization helpers shared by API routers and services."""

from datetime import date, datetime
from decimal import Decimal
import json
from uuid import UUID

import pandas as pd


def dataframe_records(df: pd.DataFrame):
    if df.empty:
        return []

    clean_df = df.where(pd.notna(df), None)
    return [serialize_value(row) for row in clean_df.to_dict(orient="records")]


def serialize_value(value):
    if isinstance(value, dict):
        return {key: serialize_value(item) for key, item in value.items()}

    if isinstance(value, list):
        return [serialize_value(item) for item in value]

    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, memoryview):
        return value.tobytes().hex()

    if isinstance(value, (bytes, bytearray)):
        return bytes(value).hex()

    if pd.isna(value):
        return None

    return value


def parse_json_list(value):
    if not value:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []
    return []

