"""Configuration for importing SNCB GTFS files into Azure SQL.

The order of ``columns`` must match the order used by the generated
INSERT statement. A ``source_columns`` entry is only needed when a
database column has a different name in the GTFS source file.
"""

BATCH_SIZE = 10_000

# Parent tables must be imported before tables that reference them.
IMPORT_ORDER = (
    "agencies",
    "routes",
    "services",
    "stops",
    "trips",
    "stop_times",
    "service_exceptions",
)

TABLE_CONFIG = {
    "agencies": {
        "source_file": "agency.txt",
        "columns": (
            "agency_id",
            "agency_lang",
            "agency_name",
            "agency_timezone",
            "agency_url",
            "agency_phone",
            "agency_fare_url",
        ),
        "integer_columns": (),
        "real_columns": (),
        "date_columns": (),
        "source_columns": {},
        "conflict_columns": ("agency_id",),
    },
    "routes": {
        "source_file": "routes.txt",
        "columns": (
            "route_id",
            "agency_id",
            "route_short_name",
            "route_long_name",
            "route_desc",
            "route_type",
            "route_url",
            "route_color",
            "route_text_color",
        ),
        "integer_columns": ("route_type",),
        "real_columns": (),
        "date_columns": (),
        "source_columns": {},
        "conflict_columns": ("route_id",),
    },
    "services": {
        "source_file": "calendar.txt",
        "columns": (
            "service_id",
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
            "start_date",
            "end_date",
        ),
        "integer_columns": (
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ),
        "real_columns": (),
        "date_columns": ("start_date", "end_date"),
        "source_columns": {},
        "conflict_columns": ("service_id",),
    },
    "stops": {
        "source_file": "stops.txt",
        "columns": (
            "stop_id",
            "parent_station",
            "stop_code",
            "stop_name",
            "stop_desc",
            "stop_lat",
            "stop_lon",
            "location_type",
            "platform_code",
            "stop_url",
            "wheelchair_boarding",
            "zone_id",
        ),
        "integer_columns": (
            "location_type",
            "wheelchair_boarding",
        ),
        "real_columns": ("stop_lat", "stop_lon"),
        "date_columns": (),
        "source_columns": {},
        "conflict_columns": ("stop_id",),
    },
    "trips": {
        "source_file": "trips.txt",
        "columns": (
            "trip_id",
            "route_id",
            "service_id",
            "trip_headsign",
            "trip_short_name",
            "direction_id",
            "block_id",
            "shape_id",
            "wheelchair_accessible",
            "bikes_allowed",
        ),
        "integer_columns": (
            "direction_id",
            "wheelchair_accessible",
            "bikes_allowed",
        ),
        "real_columns": (),
        "date_columns": (),
        "source_columns": {},
        "conflict_columns": ("trip_id",),
    },
    "stop_times": {
        "source_file": "stop_times.txt",
        "columns": (
            "trip_id",
            "stop_sequence",
            "stop_id",
            "arrival_time",
            "departure_time",
            "stop_headsign",
            "pickup_type",
            "drop_off_type",
            "shape_dist_traveled",
        ),
        "integer_columns": (
            "stop_sequence",
            "pickup_type",
            "drop_off_type",
        ),
        "real_columns": ("shape_dist_traveled",),
        "date_columns": (),
        "source_columns": {},
        "conflict_columns": ("trip_id", "stop_sequence"),
    },
    "service_exceptions": {
        "source_file": "calendar_dates.txt",
        "columns": (
            "service_id",
            "exception_date",
            "exception_type",
        ),
        "integer_columns": ("exception_type",),
        "real_columns": (),
        "date_columns": ("exception_date",),
        "source_columns": {
            "exception_date": "date",
        },
        "conflict_columns": ("service_id", "exception_date"),
    },
}
