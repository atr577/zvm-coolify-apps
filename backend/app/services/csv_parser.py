"""CSV parser service for Template project type.

Handles:
- Arbitrary columns (user-defined)
- Cyrillic and UTF-8 encoding
- BOM detection and removal
- Empty rows/columns cleanup
"""

import csv
import io
import codecs
from typing import List, Dict, Any, Tuple


class CSVParseError(Exception):
    """Raised when CSV parsing fails."""
    pass


def detect_encoding(content: bytes) -> str:
    """Detect encoding from BOM or default to UTF-8."""
    # Check for BOM markers
    if content.startswith(codecs.BOM_UTF8):
        return "utf-8-sig"
    if content.startswith(codecs.BOM_UTF16_LE) or content.startswith(codecs.BOM_UTF16_BE):
        return "utf-16"

    # Try UTF-8 first
    try:
        content.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        pass

    # Fallback to cp1251 (common for Cyrillic Windows files)
    try:
        content.decode("cp1251")
        return "cp1251"
    except UnicodeDecodeError:
        pass

    # Last resort: latin-1 (accepts any byte sequence)
    return "latin-1"


def detect_delimiter(sample: str) -> str:
    """Detect CSV delimiter from sample text."""
    # Count occurrences of common delimiters
    delimiters = [",", ";", "\t", "|"]
    counts = {d: sample.count(d) for d in delimiters}

    # Return delimiter with highest count
    return max(counts, key=counts.get)


def parse_csv(content: bytes) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Parse CSV content into column names and row data.

    Args:
        content: Raw CSV file bytes

    Returns:
        Tuple of (column_names, rows) where:
        - column_names: List of column headers
        - rows: List of dicts {column_name: value}

    Raises:
        CSVParseError: If CSV is invalid or empty
    """
    if not content or len(content.strip()) == 0:
        raise CSVParseError("CSV file is empty")

    # Detect and decode
    encoding = detect_encoding(content)
    try:
        text = content.decode(encoding)
    except UnicodeDecodeError as e:
        raise CSVParseError(f"Failed to decode CSV: {e}")

    # Remove any leading/trailing whitespace
    text = text.strip()

    if not text:
        raise CSVParseError("CSV file is empty")

    # Detect delimiter
    first_line = text.split("\n")[0]
    delimiter = detect_delimiter(first_line)

    # Parse CSV
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)

    # Get column names
    if not reader.fieldnames:
        raise CSVParseError("CSV has no header row")

    # Build mapping: original fieldname -> cleaned fieldname
    original_fieldnames = list(reader.fieldnames)
    fieldname_map = {}  # original -> cleaned
    columns = []
    for orig in original_fieldnames:
        if orig and orig.strip():
            cleaned = orig.strip()
            fieldname_map[orig] = cleaned
            columns.append(cleaned)

    if not columns:
        raise CSVParseError("CSV has no valid columns")

    # Parse rows
    rows = []
    for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
        # Clean row data
        cleaned_row = {}
        has_data = False

        for orig, cleaned in fieldname_map.items():
            value = row.get(orig, "")  # Use original fieldname to get value
            if value is not None:
                value = str(value).strip()
                cleaned_row[cleaned] = value  # Store with cleaned name
                if value:
                    has_data = True
            else:
                cleaned_row[cleaned] = ""

        # Skip completely empty rows
        if has_data:
            rows.append(cleaned_row)

    if not rows:
        raise CSVParseError("CSV has no data rows")

    return columns, rows


def validate_csv_for_project(
    columns: List[str],
    rows: List[Dict[str, Any]],
    max_rows: int = 10000
) -> None:
    """
    Validate parsed CSV data for project use.

    Args:
        columns: Column names
        rows: Row data
        max_rows: Maximum allowed rows

    Raises:
        CSVParseError: If validation fails
    """
    if len(rows) > max_rows:
        raise CSVParseError(f"CSV has too many rows ({len(rows)}). Maximum is {max_rows}.")

    if len(columns) > 50:
        raise CSVParseError(f"CSV has too many columns ({len(columns)}). Maximum is 50.")

    # Check for duplicate column names
    if len(columns) != len(set(columns)):
        duplicates = [col for col in columns if columns.count(col) > 1]
        raise CSVParseError(f"CSV has duplicate column names: {', '.join(set(duplicates))}")
