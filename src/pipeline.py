from datetime import datetime, timezone 
from src.irail_client import fetch_liveboard
from src.database import save_liveboard_data 



def unix_timestamp_to_datetime(value):
    """Convert Unix seconds to a timezone-aware UTC datetime."""
    return datetime.fromtimestamp(
        int(value),
        tz=timezone.utc,
    )

def string_flag_to_bool(value):
    """Convert an iRail zero/one string into a Boolean."""
    return bool(int(value))

def optional_string_flag_to_bool(value):
    """Convert an optional iRail zero/one value into a Boolean."""
    if value in (None, ""):
        return None
    return string_flag_to_bool(value)


def optional_float(value):
    """Convert a value to float while preserving missing values."""
    if value in (None, ""):
        return None
    return float(value)

def transform_station(station_info):
    """Transform iRail station information for Azure SQL."""

    return{
        "station_id": station_info["id"],
        "station_uri": station_info.get("@id"),
        "standard_name": (
            station_info.get("standardname")
            or station_info["name"]
        ),
        "display_name": station_info["name"],
            "longitude": optional_float(
            station_info.get("locationX")
        ),
        "latitude": optional_float(
            station_info.get("locationY")
        ),
    }

def transform_vehicle(departure):
    vehicle_info = departure["vehicleinfo"]

    return {
        "vehicle_id": departure["vehicle"],
        "short_name": vehicle_info.get("shortname"),
        "vehicle_uri": vehicle_info.get("@id"),
    }

def transform_liveboard_record(
    departure,
    origin_station_id,
    api_timestamp,
):
    """Transform one iRail departure for the liveboard_records table."""

    destination_info = departure["stationinfo"]
    platform_info = departure.get("platforminfo", {})
    occupancy_info = departure.get("occupancy", {})

    if isinstance(occupancy_info, dict):
        occupancy = occupancy_info.get("name")
    else:
        occupancy = occupancy_info

    return {
        "origin_station_id": origin_station_id,
        "destination_station_id": destination_info.get("id"),
        "destination_name": (
            destination_info.get("name")
            or departure["station"]
        ),
        "vehicle_id": departure["vehicle"],
        "scheduled_departure_at": unix_timestamp_to_datetime(
            departure["time"]
        ),
        "delay_seconds": int(departure.get("delay", 0) or 0),
        "platform": platform_info.get("name") or departure.get("platform"),
        "platform_is_normal": optional_string_flag_to_bool(
            platform_info.get("normal")
        ),
        "is_cancelled": string_flag_to_bool(
            departure.get("canceled", 0)
        ),
        "has_left": string_flag_to_bool(
            departure.get("left", 0)
        ),
        "occupancy": occupancy,
        "departure_connection": departure.get("departureConnection"),
        "api_observed_at": unix_timestamp_to_datetime(api_timestamp),
    }
def transform_liveboard(liveboard):
    """Transform a complete iRail liveboard into database-ready rows."""

    origin_station = transform_station(liveboard["stationinfo"])
    origin_station_id = origin_station["station_id"]
    api_timestamp = liveboard["timestamp"]

    departures = liveboard.get(
        "departures",
        {},
    ).get(
        "departure",
        [],
    )

    stations = {
        origin_station_id: origin_station,
    }
    vehicles = {}
    records = []

    for departure in departures:
        destination_station = transform_station(
            departure["stationinfo"]
        )
        stations[destination_station["station_id"]] = (
            destination_station
        )

        vehicle = transform_vehicle(departure)
        vehicles[vehicle["vehicle_id"]] = vehicle

        record = transform_liveboard_record(
            departure,
            origin_station_id,
            api_timestamp,
        )
        records.append(record)

    return {
        "stations": list(stations.values()),
        "vehicles": list(vehicles.values()),
        "records": records,
    }

def run_pipeline(station):
    """Fetch, transform, and save liveboard data."""

    liveboard = fetch_liveboard(station)
    transformed = transform_liveboard(liveboard)
    database_result = save_liveboard_data(transformed)
    station_info = liveboard["stationinfo"]

    return {
        "status": "liveboard ingested",
        "requested_station": station,
        "station": station_info["name"],
        "station_id": station_info["id"],
        "api_timestamp": liveboard.get("timestamp"),
        "departures_received": len(transformed["records"]),
        "stations_processed": database_result[
            "stations_processed"
        ],
        "vehicles_processed": database_result[
            "vehicles_processed"
        ],
        "records_transformed": len(transformed["records"]),
        "records_inserted": database_result[
            "records_inserted"
        ],
    }