"""Helpers to build register bitfields."""
from ..decode import RegField


def bit(
    name: str,
    low: int,
    values: tuple[tuple[int, str], ...] = (),
    description: str = "",
) -> RegField:
    """A single-bit field.

    Parameters:
        name (str): Field name.
        low (int): The bit position.
        values (tuple[tuple[int, str], ...]): Optional value names.
        description (str): Human description (from GBATEK).

    Returns:
        RegField: The field.
    """
    return RegField(name, low, low, values, description)


def bits(
    name: str,
    low: int,
    high: int,
    values: tuple[tuple[int, str], ...] = (),
    description: str = "",
) -> RegField:
    """A multi-bit field.

    Parameters:
        name (str): Field name.
        low (int): The lowest bit.
        high (int): The highest bit (inclusive).
        values (tuple[tuple[int, str], ...]): Optional value names.
        description (str): Human description (from GBATEK).

    Returns:
        RegField: The field.
    """
    return RegField(name, low, high, values, description)
