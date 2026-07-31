import json
import logging
import azure.functions as func
from src.pipeline import run_pipeline

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
SCHEDULED_STATIONS = (
    "Antwerp-Central",
    "Gent-Sint-Pieters",
    "Liège-Guillemins",
)


@app.route(
    route= "ingest_liveboard",
    methods = ["GET"],
)

def ingest_liveboard(
    req: func.HttpRequest,
    ) -> func.HttpResponse:
    """Fetch a station liveboard and store it in Azure SQL"""
    station = req.params.get(
        "station",
        "Antwerp-Central",
    ).strip()

    if not station:
        return func.HttpResponse(
            json.dumps({
                "error": "The station parameter cannot be empty."
            }),
            status_code = 400,
            mimetype = "application/json",
        )
    logging.info(
        "Starting liveboard ingestion for station: %s",
        station,
        )

    try: 
        result = run_pipeline(station)
    except Exception:
        logging.exception(
            "Liveboard ingestion failed for station: %s",
            station,
        )
        return func.HttpResponse(
            json.dumps({
                "error": "Liveboard ingestion failed.",
                "station": station,
            }),
            status_code = 500,
            mimetype = "application/json",
        )

    return func.HttpResponse(
        json.dumps(result),
        status_code = 200,
        mimetype = "application/json",
    ) 

@app.timer_trigger(
    schedule = "0 */30 * * * *",
    arg_name = "timer", 
    run_on_startup = False,
    use_monitor = True, 
)

def scheduled_liveboard_ingestion(
    timer: func.TimerRequest,
    ) -> None:
    """Ingest liveboards for multiple stations every 30 minutes."""
    if timer.past_due:
        logging.warning("The liveboard timer execution is past due.")

    successful_stations = 0
    failed_stations = 0

    logging.info(
        "Starting scheduled ingestion for %s stations.",
        len(SCHEDULED_STATIONS),
    )

    for station in SCHEDULED_STATIONS:
        try:
            result = run_pipeline(station)
        except Exception:
            failed_stations += 1 
            logging.exception(
                "Scheduled ingestion failed for station: %s",
                station,
            )
            continue

        successful_stations += 1 

        logging.info(
            "Scheduled ingestion succeeded for %s:"
            " %s records inserted.",
            station,
            result["records_inserted"],
        )

    logging.info(
        "Scheduled ingestion completed: "
        "%s stations succeeded, %s stations failed.",
        successful_stations,
        failed_stations, 
    )

