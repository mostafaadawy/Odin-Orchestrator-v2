import csv
from io import StringIO


def convert(text):
    """
    Convert CSV text with header row to a list of dictionaries.

    Args:
        text: CSV formatted string with header row as first line

    Returns:
        List of dictionaries, one per data row with header names as keys
    """
    if not text or not text.strip():
        return []

    reader = csv.DictReader(StringIO(text))
    return list(reader)
