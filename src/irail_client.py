import requests


IRAIL_LIVEBOARD_URL = "https://api.irail.be/liveboard/"
REQUEST_TIMEOUT_SECONDS = 20


class IRailClientError(RuntimeError):
    """Raised when liveboard data cannot be retrieved."""


def fetch_liveboard(station):
    """Fetch live departure data for one station."""

    params = {
        "station": station,
        "format": "json",
        "lang": "en",
        "arrdep": "departure",
        "alerts": "false",
    }

    headers = {
        "Accept": "application/json",
        "User-Agent": "railpulse-challenge-azure/1.0",
    }

    try:
        response = requests.get(
            IRAIL_LIVEBOARD_URL,
            params=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise IRailClientError(
            f"Could not retrieve the liveboard for {station}."
        ) from error

    try:
        liveboard = response.json()
    except requests.exceptions.JSONDecodeError as error:
        raise IRailClientError(
            "iRail returned an invalid JSON response."
        ) from error

    if "stationinfo" not in liveboard:
        raise IRailClientError(
            "The iRail response does not contain station information."
        )

    return liveboard