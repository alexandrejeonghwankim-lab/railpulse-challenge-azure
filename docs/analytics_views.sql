/*
RailPulse - BI-ready Azure SQL views.

The views connect live iRail observations to SNCB GTFS stations, expose
analysis-friendly delay fields, and provide a latest-status dataset without
discarding the historical observation snapshots.
*/

CREATE OR ALTER VIEW dbo.vw_station_gtfs_map
AS
SELECT
    live.station_id AS irail_station_id,
    RIGHT(live.station_id, 7) AS shared_station_code,
    live.standard_name AS irail_standard_name,
    live.display_name AS irail_display_name,
    live.latitude AS irail_latitude,
    live.longitude AS irail_longitude,

    gtfs.stop_id AS gtfs_stop_id,
    gtfs.stop_name AS gtfs_stop_name,
    gtfs.stop_code AS gtfs_stop_code,
    gtfs.stop_lat AS gtfs_latitude,
    gtfs.stop_lon AS gtfs_longitude,

    CAST(
        CASE
            WHEN gtfs.stop_id IS NOT NULL THEN 1
            ELSE 0
        END
        AS BIT
    ) AS is_gtfs_mapped
FROM dbo.stations AS live
LEFT JOIN dbo.stops AS gtfs
    ON gtfs.location_type = 1
   AND RIGHT(gtfs.stop_id, 7) = RIGHT(live.station_id, 7);
GO


CREATE OR ALTER VIEW dbo.vw_liveboard_analytics
AS
SELECT
    live.record_id,

    live.origin_station_id,
    origin_map.irail_display_name AS origin_station_name,
    origin_map.gtfs_stop_id AS origin_gtfs_stop_id,
    origin_map.is_gtfs_mapped AS origin_is_gtfs_mapped,

    live.destination_station_id,
    live.destination_name,
    destination_map.gtfs_stop_id AS destination_gtfs_stop_id,
    destination_map.is_gtfs_mapped AS destination_is_gtfs_mapped,

    live.vehicle_id,
    vehicle.short_name AS vehicle_short_name,

    live.scheduled_departure_at,
    DATEADD(
        SECOND,
        live.delay_seconds,
        live.scheduled_departure_at
    ) AS estimated_departure_at,

    CAST(live.scheduled_departure_at AS DATE) AS departure_date,
    DATEPART(HOUR, live.scheduled_departure_at) AS departure_hour,

    live.delay_seconds,
    CAST(live.delay_seconds / 60.0 AS DECIMAL(10, 2))
        AS delay_minutes,

    CAST(
        CASE
            WHEN live.is_cancelled = 0
             AND live.delay_seconds < 120
            THEN 1
            ELSE 0
        END
        AS BIT
    ) AS is_on_time,

    live.platform,
    live.platform_is_normal,
    live.is_cancelled,
    live.has_left,
    live.occupancy,
    live.departure_connection,
    live.api_observed_at,
    live.ingested_at_utc
FROM dbo.liveboard_records AS live
INNER JOIN dbo.vw_station_gtfs_map AS origin_map
    ON origin_map.irail_station_id = live.origin_station_id
LEFT JOIN dbo.vw_station_gtfs_map AS destination_map
    ON destination_map.irail_station_id =
       live.destination_station_id
INNER JOIN dbo.vehicles AS vehicle
    ON vehicle.vehicle_id = live.vehicle_id;
GO


CREATE OR ALTER VIEW dbo.vw_latest_liveboard_status
AS
WITH ranked_observations AS (
    SELECT
        record_id,
        ROW_NUMBER() OVER (
            PARTITION BY
                origin_station_id,
                vehicle_id,
                scheduled_departure_at
            ORDER BY
                api_observed_at DESC,
                record_id DESC
        ) AS observation_rank
    FROM dbo.liveboard_records
)
SELECT analytics.*
FROM dbo.vw_liveboard_analytics AS analytics
INNER JOIN ranked_observations AS ranked
    ON ranked.record_id = analytics.record_id
WHERE ranked.observation_rank = 1;
GO


/* Validation */

SELECT
    is_gtfs_mapped,
    COUNT_BIG(*) AS station_count
FROM dbo.vw_station_gtfs_map
GROUP BY is_gtfs_mapped
ORDER BY is_gtfs_mapped DESC;

SELECT
    (SELECT COUNT_BIG(*) FROM dbo.vw_liveboard_analytics)
        AS historical_observations,
    (SELECT COUNT_BIG(*) FROM dbo.vw_latest_liveboard_status)
        AS latest_departures;
