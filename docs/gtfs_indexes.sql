/*
RailPulse - secondary indexes for the migrated SNCB GTFS tables.

Run this script after loading the GTFS text files. Primary-key indexes are
created by gtfs_schema_azure.sql; these indexes support foreign-key joins,
station lookups, date filtering, and Power BI queries.
*/

SET XACT_ABORT ON;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = N'IX_routes_agency_id'
      AND object_id = OBJECT_ID(N'dbo.routes')
)
BEGIN
    CREATE INDEX IX_routes_agency_id
        ON dbo.routes (agency_id);
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = N'IX_stops_parent_station'
      AND object_id = OBJECT_ID(N'dbo.stops')
)
BEGIN
    CREATE INDEX IX_stops_parent_station
        ON dbo.stops (parent_station);
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = N'IX_stops_stop_code'
      AND object_id = OBJECT_ID(N'dbo.stops')
)
BEGIN
    CREATE INDEX IX_stops_stop_code
        ON dbo.stops (stop_code);
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = N'IX_trips_route_id'
      AND object_id = OBJECT_ID(N'dbo.trips')
)
BEGIN
    CREATE INDEX IX_trips_route_id
        ON dbo.trips (route_id);
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = N'IX_trips_service_id'
      AND object_id = OBJECT_ID(N'dbo.trips')
)
BEGIN
    CREATE INDEX IX_trips_service_id
        ON dbo.trips (service_id);
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = N'IX_service_exceptions_exception_date'
      AND object_id = OBJECT_ID(N'dbo.service_exceptions')
)
BEGIN
    CREATE INDEX IX_service_exceptions_exception_date
        ON dbo.service_exceptions (
            exception_date,
            exception_type
        );
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = N'IX_stop_times_stop_id'
      AND object_id = OBJECT_ID(N'dbo.stop_times')
)
BEGIN
    CREATE INDEX IX_stop_times_stop_id
        ON dbo.stop_times (
            stop_id,
            departure_time
        )
        INCLUDE (
            trip_id,
            stop_sequence,
            arrival_time
        );
END;


/* Validation: seven rows should be returned. */

SELECT
    table_name = OBJECT_NAME(i.object_id),
    index_name = i.name
FROM sys.indexes AS i
WHERE i.name IN (
    N'IX_routes_agency_id',
    N'IX_stops_parent_station',
    N'IX_stops_stop_code',
    N'IX_trips_route_id',
    N'IX_trips_service_id',
    N'IX_service_exceptions_exception_date',
    N'IX_stop_times_stop_id'
)
ORDER BY table_name, index_name;
