"""Seed database with sample data for development.

Usage:
    python -m src.db.seed --check-empty

When --check-empty is passed, only seeds if the database has no customer rows.
Currently a stub — will insert sample CustomerProfile rows once ORM models exist.
"""

from __future__ import annotations

import argparse
import sys

import structlog

logger = structlog.get_logger()


def main() -> None:
    """Run the seeding logic."""
    parser = argparse.ArgumentParser(description="Seed the database")
    parser.add_argument(
        "--check-empty",
        action="store_true",
        help="Only seed if database is empty",
    )
    args = parser.parse_args()

    if args.check_empty:
        logger.info("seed_check", status="no ORM models yet — nothing to seed")
        return

    logger.info("seed_run", status="seeding not implemented yet (no ORM models)")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logger.error("seed_error", error=str(exc))
        sys.exit(1)
