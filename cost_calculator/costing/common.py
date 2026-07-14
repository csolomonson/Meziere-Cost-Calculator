import pandas as pd


def first_value(df: pd.DataFrame, column: str, default=None):
    if df.empty or column not in df.columns:
        return default

    value = df.iloc[0][column]
    if pd.isna(value):
        return default

    return value


def number(value, default=0.0):
    if value is None or pd.isna(value):
        return default

    return value


def markup_multiplier(value):
    value = number(value, 1.0)
    return value
