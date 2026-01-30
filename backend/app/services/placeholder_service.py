"""Placeholder replacement service for Template project type.

Replaces {column_name} placeholders in text with actual values from variant data.
"""

import re
from typing import Dict, Any, List, Set


class PlaceholderError(Exception):
    """Raised when placeholder replacement fails."""
    pass


# Pattern to match {column_name} placeholders
PLACEHOLDER_PATTERN = re.compile(r"\{([^{}]+)\}")


def extract_placeholders(text: str) -> Set[str]:
    """
    Extract all placeholder names from text.

    Args:
        text: Text containing {placeholder} patterns

    Returns:
        Set of placeholder names (without braces)
    """
    return set(PLACEHOLDER_PATTERN.findall(text))


def replace_placeholders(
    text: str,
    data: Dict[str, Any],
    strict: bool = True
) -> str:
    """
    Replace {column_name} placeholders with values from data dict.

    Args:
        text: Text containing {placeholder} patterns
        data: Dict of column_name -> value
        strict: If True, raise error for missing placeholders

    Returns:
        Text with placeholders replaced

    Raises:
        PlaceholderError: If strict=True and placeholder not found in data
    """
    def replacer(match: re.Match) -> str:
        key = match.group(1)
        if key in data:
            value = data[key]
            return str(value) if value is not None else ""
        elif strict:
            raise PlaceholderError(f"Placeholder '{{{key}}}' not found in variant data")
        else:
            return match.group(0)  # Keep original placeholder

    return PLACEHOLDER_PATTERN.sub(replacer, text)


def validate_placeholders(
    text: str,
    available_columns: List[str]
) -> List[str]:
    """
    Validate that all placeholders in text exist in available columns.

    Args:
        text: Text containing {placeholder} patterns
        available_columns: List of valid column names

    Returns:
        List of missing placeholder names (empty if all valid)
    """
    placeholders = extract_placeholders(text)
    available_set = set(available_columns)
    missing = [p for p in placeholders if p not in available_set]
    return missing


def prepare_prompt(
    template: str,
    variant_data: Dict[str, Any],
    strict: bool = True
) -> str:
    """
    Prepare a prompt by replacing placeholders with variant data.

    This is a convenience wrapper around replace_placeholders.

    Args:
        template: Prompt template with {placeholder} patterns
        variant_data: Dict from Variant.data JSON field
        strict: If True, raise error for missing placeholders

    Returns:
        Filled prompt with placeholders replaced
    """
    return replace_placeholders(template, variant_data, strict=strict)
