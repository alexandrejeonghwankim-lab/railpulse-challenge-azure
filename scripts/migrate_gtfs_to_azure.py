"""Import selected SNCB GTFS text files into Azure SQL."""

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database import get_connection
from gtfs_import_config import (
    BATCH_SIZE,
    IMPORT_ORDER,
    TABLE_CONFIG,
)


def parse_arguments():
    """Read the data-directory and table selections."""

    parser = argparse.ArgumentParser(
        description="Import SNCB GTFS files into Azure SQL."
    )

    parser.add_argument(
        "--data-dir",
        required=True,
        type=Path,
        help="Directory containing the GTFS text files.",
    )

    parser.add_argument(
        "--tables",
        required=True,
        nargs="+",
        choices=TABLE_CONFIG.keys(),
        help="One or more configured tables to import.",
    )

    return parser.parse_args()


def expected_source_columns(config):
    """Return the GTFS columns required for one table."""

    return {
        config["source_columns"].get(
            database_column,
            database_column,
        )
        for database_column in config["columns"]
    }


def validate_source_file(
    table_name,
    data_directory,
):
    """Validate one GTFS source file and return its path."""

    config = TABLE_CONFIG[table_name]
    source_path = data_directory / config["source_file"]

    if not source_path.is_file():
        raise FileNotFoundError(
            f"Missing GTFS file: {source_path}"
        )

    with source_path.open(
        mode="r",
        encoding="utf-8-sig",
        newline="",
    ) as source_file:
        reader = csv.DictReader(source_file)
        actual_columns = set(reader.fieldnames or [])

    required_columns = expected_source_columns(config)
    missing_columns = required_columns - actual_columns

    if missing_columns:
        raise ValueError(
            f"{config['source_file']} is missing columns: "
            f"{sorted(missing_columns)}"
        )

    print(
        f"[VALID] {table_name}: "
        f"{config['source_file']}"
    )

    return source_path


def empty_to_none(value):
    """Convert an empty GTFS value into SQL NULL."""

    if value == "":
        return None

    return value


def convert_gtfs_date(value):
    """Convert YYYYMMDD into a Python date."""

    return datetime.strptime(
        value,
        "%Y%m%d",
    ).date()


def convert_value(
    value,
    database_column,
    config,
):
    """Convert one GTFS value for Azure SQL."""

    value = empty_to_none(value)

    if value is None:
        return None

    if database_column in config["integer_columns"]:
        return int(value)

    if database_column in config["real_columns"]:
        return float(value)

    if database_column in config["date_columns"]:
        return convert_gtfs_date(value)

    return value


def prepare_row(
    source_row,
    config,
):
    """Convert one GTFS dictionary into an ordered tuple."""

    values = []

    for database_column in config["columns"]:
        source_column = config["source_columns"].get(
            database_column,
            database_column,
        )

        values.append(
            convert_value(
                source_row[source_column],
                database_column,
                config,
            )
        )

    return tuple(values)


def build_insert_sql(
    table_name,
    config,
):
    """Build a parameterized Azure SQL INSERT statement."""

    column_names = ", ".join(
        f"[{column}]"
        for column in config["columns"]
    )

    placeholders = ", ".join(
        "?"
        for _ in config["columns"]
    )

    return f"""
        INSERT INTO dbo.[{table_name}] (
            {column_names}
        )
        VALUES (
            {placeholders}
        );
    """


def iter_source_rows(
    table_name,
    source_path,
):
    """Yield source rows, placing parent stops before platforms."""

    passes = (None,)

    if table_name == "stops":
        passes = (
            "parent_stations",
            "child_stops",
        )

    for current_pass in passes:
        with source_path.open(
            mode="r",
            encoding="utf-8-sig",
            newline="",
        ) as source_file:
            reader = csv.DictReader(source_file)

            for source_row in reader:
                if current_pass == "parent_stations":
                    if source_row.get("parent_station", ""):
                        continue

                if current_pass == "child_stops":
                    if not source_row.get("parent_station", ""):
                        continue

                yield source_row


def get_table_row_count(
    connection,
    table_name,
):
    """Return the current Azure SQL row count."""

    cursor = connection.cursor()

    cursor.execute(
        f"SELECT COUNT_BIG(*) "
        f"FROM dbo.[{table_name}];"
    )

    return cursor.fetchone()[0]


def write_batch(
    connection,
    cursor,
    insert_sql,
    batch,
):
    """Insert and commit one batch."""

    cursor.executemany(
        insert_sql,
        batch,
    )

    connection.commit()

    written_count = len(batch)
    batch.clear()

    return written_count


def import_table(
    connection,
    table_name,
    data_directory,
):
    """Import one complete GTFS text file."""

    current_count = get_table_row_count(
        connection,
        table_name,
    )

    if current_count > 0:
        print(
            f"[SKIPPED] {table_name} already contains "
            f"{current_count:,} rows."
        )
        return current_count

    config = TABLE_CONFIG[table_name]

    source_path = validate_source_file(
        table_name,
        data_directory,
    )

    insert_sql = build_insert_sql(
        table_name,
        config,
    )

    cursor = connection.cursor()
    cursor.fast_executemany = True

    batch = []
    processed_count = 0

    try:
        for source_row in iter_source_rows(
            table_name,
            source_path,
        ):
            batch.append(
                prepare_row(
                    source_row,
                    config,
                )
            )

            if len(batch) >= BATCH_SIZE:
                processed_count += write_batch(
                    connection,
                    cursor,
                    insert_sql,
                    batch,
                )

                print(
                    f"{table_name}: "
                    f"{processed_count:,} rows imported."
                )

        if batch:
            processed_count += write_batch(
                connection,
                cursor,
                insert_sql,
                batch,
            )

    except Exception:
        connection.rollback()
        raise

    final_count = get_table_row_count(
        connection,
        table_name,
    )

    print(
        f"[COMPLETE] {table_name}: "
        f"{final_count:,} rows in Azure SQL."
    )

    return final_count


def main():
    """Import the selected tables in dependency-safe order."""

    arguments = parse_arguments()
    data_directory = arguments.data_dir.resolve()

    if not data_directory.is_dir():
        raise NotADirectoryError(
            f"GTFS directory not found: {data_directory}"
        )

    requested_tables = set(arguments.tables)

    selected_tables = [
        table_name
        for table_name in IMPORT_ORDER
        if table_name in requested_tables
    ]

    print(f"GTFS directory: {data_directory}")
    print(f"Selected tables: {', '.join(selected_tables)}")

    connection = get_connection()

    try:
        for table_name in selected_tables:
            print()
            print(f"Importing {table_name}...")

            import_table(
                connection,
                table_name,
                data_directory,
            )
    finally:
        connection.close()

    print()
    print("Selected GTFS imports completed.")


if __name__ == "__main__":
    main()