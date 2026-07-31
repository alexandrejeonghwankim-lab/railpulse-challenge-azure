/*
RailPulse Cloud - Azure SQL schema

This schema stores live departure observations returned by the iRail
Liveboard API. It targets Microsoft Azure SQL Database (T-SQL), not SQLite.

Relationships:
    stations 1 ---- many liveboard_records (origin_station_id)
    stations 1 ---- many liveboard_records (destination_station_id)
    vehicles 1 ---- many liveboard_records
*/

SET XACT_ABORT ON;

BEGIN TRANSACTION;

IF OBJECT_ID(N'dbo.stations', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.stations (
        station_id     NVARCHAR(50)  NOT NULL,
        station_uri    NVARCHAR(500) NULL,
        standard_name  NVARCHAR(200) NOT NULL,
        display_name   NVARCHAR(200) NOT NULL,
        longitude      DECIMAL(9, 6) NULL,
        latitude       DECIMAL(9, 6) NULL,
        created_at_utc DATETIME2(0)  NOT NULL
            CONSTRAINT DF_stations_created_at_utc DEFAULT SYSUTCDATETIME(),
        updated_at_utc DATETIME2(0)  NOT NULL
            CONSTRAINT DF_stations_updated_at_utc DEFAULT SYSUTCDATETIME(),

        CONSTRAINT PK_stations PRIMARY KEY (station_id),
        CONSTRAINT CK_stations_longitude
            CHECK (longitude IS NULL OR longitude BETWEEN -180.0 AND 180.0),
        CONSTRAINT CK_stations_latitude
            CHECK (latitude IS NULL OR latitude BETWEEN -90.0 AND 90.0)
    );
END;

IF OBJECT_ID(N'dbo.vehicles', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.vehicles (
        vehicle_id     NVARCHAR(80)  NOT NULL,
        short_name     NVARCHAR(50)  NULL,
        vehicle_uri    NVARCHAR(500) NULL,
        created_at_utc DATETIME2(0)  NOT NULL
            CONSTRAINT DF_vehicles_created_at_utc DEFAULT SYSUTCDATETIME(),
        updated_at_utc DATETIME2(0)  NOT NULL
            CONSTRAINT DF_vehicles_updated_at_utc DEFAULT SYSUTCDATETIME(),

        CONSTRAINT PK_vehicles PRIMARY KEY (vehicle_id)
    );
END;

IF OBJECT_ID(N'dbo.liveboard_records', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.liveboard_records (
        record_id              BIGINT IDENTITY(1, 1) NOT NULL,
        origin_station_id      NVARCHAR(50)  NOT NULL,
        destination_station_id NVARCHAR(50)  NULL,
        destination_name       NVARCHAR(200) NOT NULL,
        vehicle_id             NVARCHAR(80)  NOT NULL,
        scheduled_departure_at DATETIMEOFFSET(0) NOT NULL,
        delay_seconds          INT           NOT NULL
            CONSTRAINT DF_liveboard_records_delay_seconds DEFAULT 0,
        platform               NVARCHAR(20)  NULL,
        platform_is_normal     BIT           NULL,
        is_cancelled           BIT           NOT NULL
            CONSTRAINT DF_liveboard_records_is_cancelled DEFAULT 0,
        has_left               BIT           NOT NULL
            CONSTRAINT DF_liveboard_records_has_left DEFAULT 0,
        occupancy              NVARCHAR(30)  NULL,
        departure_connection   NVARCHAR(500) NULL,
        api_observed_at        DATETIMEOFFSET(0) NOT NULL,
        ingested_at_utc        DATETIME2(0)  NOT NULL
            CONSTRAINT DF_liveboard_records_ingested_at_utc
            DEFAULT SYSUTCDATETIME(),

        CONSTRAINT PK_liveboard_records PRIMARY KEY (record_id),
        CONSTRAINT FK_liveboard_records_origin_station
            FOREIGN KEY (origin_station_id)
            REFERENCES dbo.stations (station_id),
        CONSTRAINT FK_liveboard_records_destination_station
            FOREIGN KEY (destination_station_id)
            REFERENCES dbo.stations (station_id),
        CONSTRAINT FK_liveboard_records_vehicle
            FOREIGN KEY (vehicle_id)
            REFERENCES dbo.vehicles (vehicle_id),
        CONSTRAINT UQ_liveboard_records_observation
            UNIQUE (
                origin_station_id,
                vehicle_id,
                scheduled_departure_at,
                api_observed_at
            )
    );
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = N'IX_liveboard_records_station_departure'
      AND object_id = OBJECT_ID(N'dbo.liveboard_records')
)
BEGIN
    CREATE INDEX IX_liveboard_records_station_departure
        ON dbo.liveboard_records (
            origin_station_id,
            scheduled_departure_at
        );
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = N'IX_liveboard_records_vehicle_departure'
      AND object_id = OBJECT_ID(N'dbo.liveboard_records')
)
BEGIN
    CREATE INDEX IX_liveboard_records_vehicle_departure
        ON dbo.liveboard_records (
            vehicle_id,
            scheduled_departure_at
        );
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = N'IX_liveboard_records_observed_at'
      AND object_id = OBJECT_ID(N'dbo.liveboard_records')
)
BEGIN
    CREATE INDEX IX_liveboard_records_observed_at
        ON dbo.liveboard_records (api_observed_at);
END;

COMMIT TRANSACTION;
