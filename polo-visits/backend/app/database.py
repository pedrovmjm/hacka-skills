"""Compatibility facade for the legacy test and tooling imports.

New code depends on the persistence port and SQLite adapter directly.
"""

from app.adapters.persistence.sqlite import (
    DB_PATH,
    connection,
    initialize_database,
    reset_database,
    row_to_dict,
    seed,
    timestamp,
)

__all__ = [
    "DB_PATH",
    "connection",
    "initialize_database",
    "reset_database",
    "row_to_dict",
    "seed",
    "timestamp",
]
