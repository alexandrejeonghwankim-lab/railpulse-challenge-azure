import os
import time

import pyodbc


SQL_CONNECTION_STRING_SETTING = "AZURE_SQL_CONNECTION_STRING"
TRANSIENT_ERROR_CODES = (
    "40197",
    "40501",
    "40613",
    "49918",
    "49919",
    "49920",
)


def is_transient_database_error(error):
    """Return True when Azure SQL indicates a temporary problem."""

    error_message = str(error)

    return any(
        code in error_message
        for code in TRANSIENT_ERROR_CODES
    )


def get_connection(
    max_attempts=6,
    retry_delay_seconds=10,
):
    """Connect to Azure SQL, retrying temporary serverless errors."""

    connection_string = os.environ.get(
        SQL_CONNECTION_STRING_SETTING
    )

    if not connection_string:
        raise RuntimeError(
            f"Missing environment variable: "
            f"{SQL_CONNECTION_STRING_SETTING}"
        )

    for attempt in range(1, max_attempts + 1):
        try:
            return pyodbc.connect(
                connection_string,
                timeout=30,
            )
        except pyodbc.Error as error:
            final_attempt = attempt == max_attempts

            if (
                final_attempt
                or not is_transient_database_error(error)
            ):
                raise

            time.sleep(retry_delay_seconds)

    raise RuntimeError("Could not connect to Azure SQL.")

def upsert_stations(cursor, stations):
    """Insert new stations or update existing stations."""

    sql = """
        UPDATE dbo.stations
        SET
            station_uri = ?,
            standard_name = ?,
            display_name = ?,
            longitude = ?,
            latitude = ?,
            updated_at_utc = SYSUTCDATETIME()
        WHERE station_id = ?;

        IF @@ROWCOUNT = 0
        BEGIN
            INSERT INTO dbo.stations (
                station_id,
                station_uri,
                standard_name,
                display_name,
                longitude,
                latitude
            )
            VALUES (?, ?, ?, ?, ?, ?);
        END;
    """

    for station in stations:
        cursor.execute(
            sql,
            station["station_uri"],
            station["standard_name"],
            station["display_name"],
            station["longitude"],
            station["latitude"],
            station["station_id"],
            station["station_id"],
            station["station_uri"],
            station["standard_name"],
            station["display_name"],
            station["longitude"],
            station["latitude"],
        )

    return len(stations)


def upsert_vehicles(cursor, vehicles):
    """Insert new vehicles or update existing vehicles."""

    sql = """
        UPDATE dbo.vehicles
        SET
            short_name = ?,
            vehicle_uri = ?,
            updated_at_utc = SYSUTCDATETIME()
        WHERE vehicle_id = ?;

        IF @@ROWCOUNT = 0
        BEGIN
            INSERT INTO dbo.vehicles (
                vehicle_id,
                short_name,
                vehicle_uri
            )
            VALUES (?, ?, ?);
        END;
    """

    for vehicle in vehicles:
        cursor.execute(
            sql,
            vehicle["short_name"],
            vehicle["vehicle_uri"],
            vehicle["vehicle_id"],
            vehicle["vehicle_id"],
            vehicle["short_name"],
            vehicle["vehicle_uri"],
        )

    return len(vehicles)


def insert_liveboard_records(cursor, records):
    """Insert observations that are not already stored."""

    sql = """
        INSERT INTO dbo.liveboard_records (
            origin_station_id,
            destination_station_id,
            destination_name,
            vehicle_id,
            scheduled_departure_at,
            delay_seconds,
            platform,
            platform_is_normal,
            is_cancelled,
            has_left,
            occupancy,
            departure_connection,
            api_observed_at
        )
        OUTPUT INSERTED.record_id
        SELECT
            ?, ?, ?, ?,
            CONVERT(DATETIMEOFFSET(0), ?),
            ?, ?, ?, ?, ?, ?, ?,
            CONVERT(DATETIMEOFFSET(0), ?)
        WHERE NOT EXISTS (
            SELECT 1
            FROM dbo.liveboard_records
            WHERE origin_station_id = ?
              AND vehicle_id = ?
              AND scheduled_departure_at =
                  CONVERT(DATETIMEOFFSET(0), ?)
              AND api_observed_at =
                  CONVERT(DATETIMEOFFSET(0), ?)
        );
    """

    inserted_count = 0

    for record in records:
        scheduled_departure = (
            record["scheduled_departure_at"].isoformat()
        )
        api_observed = record["api_observed_at"].isoformat()

        cursor.execute(
            sql,
            record["origin_station_id"],
            record["destination_station_id"],
            record["destination_name"],
            record["vehicle_id"],
            scheduled_departure,
            record["delay_seconds"],
            record["platform"],
            record["platform_is_normal"],
            record["is_cancelled"],
            record["has_left"],
            record["occupancy"],
            record["departure_connection"],
            api_observed,
            record["origin_station_id"],
            record["vehicle_id"],
            scheduled_departure,
            api_observed,
        )

        if cursor.fetchone() is not None:
            inserted_count += 1

    return inserted_count


def save_liveboard_data(transformed):
    """Save one transformed liveboard in a single transaction."""

    connection = get_connection()

    try:
        cursor = connection.cursor()

        stations_processed = upsert_stations(
            cursor,
            transformed["stations"],
        )
        vehicles_processed = upsert_vehicles(
            cursor,
            transformed["vehicles"],
        )
        records_inserted = insert_liveboard_records(
            cursor,
            transformed["records"],
        )

        connection.commit()

        return {
            "stations_processed": stations_processed,
            "vehicles_processed": vehicles_processed,
            "records_inserted": records_inserted,
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()