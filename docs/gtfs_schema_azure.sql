/*
RailPulse — Sprint 1 GTFS Static Schema for Azure SQL

Source files:
    agency.txt
    routes.txt
    calendar.txt
    calendar_dates.txt
    stops.txt
    trips.txt
    stop_times.txt

This is Microsoft T-SQL, not SQLite.
GTFS arrival and departure times remain VARCHAR because GTFS permits
values beyond 24:00:00.
*/

SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.agencies', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.agencies (
            agency_id       NVARCHAR(100)  NOT NULL,
            agency_lang     NVARCHAR(20)   NULL,
            agency_name     NVARCHAR(300)  NOT NULL,
            agency_timezone NVARCHAR(100)  NOT NULL,
            agency_url      NVARCHAR(1000) NOT NULL,
            agency_phone    NVARCHAR(100)  NULL,
            agency_fare_url NVARCHAR(1000) NULL,

            CONSTRAINT PK_agencies
                PRIMARY KEY (agency_id)
        );
    END;

    IF OBJECT_ID(N'dbo.services', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.services (
            service_id NVARCHAR(200) NOT NULL,
            monday     BIT           NOT NULL,
            tuesday    BIT           NOT NULL,
            wednesday  BIT           NOT NULL,
            thursday   BIT           NOT NULL,
            friday     BIT           NOT NULL,
            saturday   BIT           NOT NULL,
            sunday     BIT           NOT NULL,
            start_date DATE          NOT NULL,
            end_date   DATE          NOT NULL,

            CONSTRAINT PK_services
                PRIMARY KEY (service_id),

            CONSTRAINT CK_services_date_range
                CHECK (end_date >= start_date)
        );
    END;

    IF OBJECT_ID(N'dbo.routes', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.routes (
            route_id         NVARCHAR(200)  NOT NULL,
            agency_id        NVARCHAR(100)  NOT NULL,
            route_short_name NVARCHAR(200)  NOT NULL,
            route_long_name  NVARCHAR(500)  NOT NULL,
            route_desc       NVARCHAR(1000) NULL,
            route_type       INT            NOT NULL,
            route_url        NVARCHAR(1000) NULL,
            route_color      NVARCHAR(20)   NULL,
            route_text_color NVARCHAR(20)   NULL,

            CONSTRAINT PK_routes
                PRIMARY KEY (route_id),

            CONSTRAINT FK_routes_agencies
                FOREIGN KEY (agency_id)
                REFERENCES dbo.agencies (agency_id),

            CONSTRAINT CK_routes_route_type
                CHECK (route_type >= 0)
        );
    END;

    IF OBJECT_ID(N'dbo.stops', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.stops (
            stop_id             NVARCHAR(200)  NOT NULL,
            parent_station      NVARCHAR(200)  NULL,
            stop_code           NVARCHAR(100)  NULL,
            stop_name           NVARCHAR(300)  NOT NULL,
            stop_desc           NVARCHAR(1000) NULL,
            stop_lat            DECIMAL(9, 6)  NOT NULL,
            stop_lon            DECIMAL(9, 6)  NOT NULL,
            location_type       TINYINT        NOT NULL
                CONSTRAINT DF_stops_location_type DEFAULT 0,
            platform_code       NVARCHAR(100)  NULL,
            stop_url            NVARCHAR(1000) NULL,
            wheelchair_boarding TINYINT        NULL,
            zone_id             NVARCHAR(100)  NULL,

            CONSTRAINT PK_stops
                PRIMARY KEY (stop_id),

            CONSTRAINT FK_stops_parent_station
                FOREIGN KEY (parent_station)
                REFERENCES dbo.stops (stop_id),

            CONSTRAINT CK_stops_latitude
                CHECK (stop_lat BETWEEN -90.0 AND 90.0),

            CONSTRAINT CK_stops_longitude
                CHECK (stop_lon BETWEEN -180.0 AND 180.0),

            CONSTRAINT CK_stops_location_type
                CHECK (location_type IN (0, 1, 2, 3, 4)),

            CONSTRAINT CK_stops_wheelchair_boarding
                CHECK (
                    wheelchair_boarding IS NULL
                    OR wheelchair_boarding IN (0, 1, 2)
                )
        );
    END;

    IF OBJECT_ID(N'dbo.trips', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.trips (
            trip_id               NVARCHAR(300)  NOT NULL,
            route_id              NVARCHAR(200)  NOT NULL,
            service_id            NVARCHAR(200)  NOT NULL,
            trip_headsign         NVARCHAR(500)  NULL,
            trip_short_name       NVARCHAR(200)  NULL,
            direction_id          TINYINT        NULL,
            block_id              NVARCHAR(200)  NULL,
            shape_id              NVARCHAR(200)  NULL,
            wheelchair_accessible TINYINT        NULL,
            bikes_allowed         TINYINT        NULL,

            CONSTRAINT PK_trips
                PRIMARY KEY (trip_id),

            CONSTRAINT FK_trips_routes
                FOREIGN KEY (route_id)
                REFERENCES dbo.routes (route_id),

            CONSTRAINT FK_trips_services
                FOREIGN KEY (service_id)
                REFERENCES dbo.services (service_id),

            CONSTRAINT CK_trips_direction
                CHECK (
                    direction_id IS NULL
                    OR direction_id IN (0, 1)
                ),

            CONSTRAINT CK_trips_wheelchair
                CHECK (
                    wheelchair_accessible IS NULL
                    OR wheelchair_accessible IN (0, 1, 2)
                ),

            CONSTRAINT CK_trips_bikes
                CHECK (
                    bikes_allowed IS NULL
                    OR bikes_allowed IN (0, 1, 2)
                )
        );
    END;

    IF OBJECT_ID(N'dbo.service_exceptions', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.service_exceptions (
            service_id     NVARCHAR(200) NOT NULL,
            exception_date DATE          NOT NULL,
            exception_type TINYINT       NOT NULL,

            CONSTRAINT PK_service_exceptions
                PRIMARY KEY (
                    service_id,
                    exception_date
                ),

            CONSTRAINT FK_service_exceptions_services
                FOREIGN KEY (service_id)
                REFERENCES dbo.services (service_id),

            CONSTRAINT CK_service_exceptions_type
                CHECK (exception_type IN (1, 2))
        );
    END;

    IF OBJECT_ID(N'dbo.stop_times', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.stop_times (
            trip_id             NVARCHAR(300) NOT NULL,
            stop_sequence       INT           NOT NULL,
            stop_id             NVARCHAR(200) NOT NULL,
            arrival_time        VARCHAR(8)    NOT NULL,
            departure_time      VARCHAR(8)    NOT NULL,
            stop_headsign       NVARCHAR(500) NULL,
            pickup_type         TINYINT       NOT NULL,
            drop_off_type       TINYINT       NOT NULL,
            shape_dist_traveled DECIMAL(18, 3) NULL,

            CONSTRAINT PK_stop_times
                PRIMARY KEY (
                    trip_id,
                    stop_sequence
                ),

            CONSTRAINT FK_stop_times_trips
                FOREIGN KEY (trip_id)
                REFERENCES dbo.trips (trip_id),

            CONSTRAINT FK_stop_times_stops
                FOREIGN KEY (stop_id)
                REFERENCES dbo.stops (stop_id),

            CONSTRAINT CK_stop_times_sequence
                CHECK (stop_sequence >= 0),

            CONSTRAINT CK_stop_times_pickup
                CHECK (pickup_type IN (0, 1, 2, 3)),

            CONSTRAINT CK_stop_times_drop_off
                CHECK (drop_off_type IN (0, 1, 2, 3)),

            CONSTRAINT CK_stop_times_distance
                CHECK (
                    shape_dist_traveled IS NULL
                    OR shape_dist_traveled >= 0
                )
        );
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    THROW;
END CATCH;


/* Validation: the seven tables should appear below. */

SELECT
    table_name = t.name
FROM sys.tables AS t
WHERE SCHEMA_NAME(t.schema_id) = N'dbo'
  AND t.name IN (
      N'agencies',
      N'routes',
      N'services',
      N'service_exceptions',
      N'stops',
      N'trips',
      N'stop_times'
  )
ORDER BY t.name;