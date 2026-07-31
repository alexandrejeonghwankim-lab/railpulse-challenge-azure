import logging
import time

import requests


IRAIL_LIVEBOARD_URL = "https://api.irail.be/liveboard/"
REQUEST_TIMEOUT_SECONDS = 20
MAX_REQUEST_ATTEMPTS = 4
INITIAL_RETRY_DELAY_SECONDS = 1
MAX_RETRY_DELAY_SECONDS = 30
RETRYABLE_STATUS_CODES = {
    429,
    500,
    502,
    503,
    504,
}


class IRailClientError(RuntimeError):
    """Raised when liveboard data cannot be retrieved."""


def get_retry_delay_seconds(response, attempt):
    """Return a bounded Retry-After or exponential delay."""

    retry_after = response.headers.get("Retry-After")

    if retry_after:
        try:
            return min(
                max(int(retry_after), 0),
                MAX_RETRY_DELAY_SECONDS,
            )
        except ValueError:
            pass

    return min(
        INITIAL_RETRY_DELAY_SECONDS * (2 ** (attempt - 1)),
        MAX_RETRY_DELAY_SECONDS,
    )


def wait_before_retry(station, attempt, delay_seconds, reason):
    """Log one transient failure and wait before retrying."""

    logging.warning(
        "Transient iRail failure for station %s on attempt %s/%s "
        "(%s). Retrying in %s seconds.",
        station,
        attempt,
        MAX_REQUEST_ATTEMPTS,
        reason,
        delay_seconds,
    )

    time.sleep(delay_seconds)


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

    response = None

    for attempt in range(1, MAX_REQUEST_ATTEMPTS + 1):
        try:
            response = requests.get(
                IRAIL_LIVEBOARD_URL,
                params=params,
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except (
            requests.ConnectionError,
            requests.Timeout,
        ) as error:
            if attempt == MAX_REQUEST_ATTEMPTS:
                raise IRailClientError(
                    f"Could not retrieve the liveboard for {station} "
                    f"after {MAX_REQUEST_ATTEMPTS} attempts."
                ) from error

            delay_seconds = min(
                INITIAL_RETRY_DELAY_SECONDS * (2 ** (attempt - 1)),
                MAX_RETRY_DELAY_SECONDS,
            )

            wait_before_retry(
                station,
                attempt,
                delay_seconds,
                type(error).__name__,
            )
            continue
        except requests.RequestException as error:
            raise IRailClientError(
                f"Could not retrieve the liveboard for {station}."
            ) from error

        if response.status_code not in RETRYABLE_STATUS_CODES:
            break

        if attempt == MAX_REQUEST_ATTEMPTS:
            raise IRailClientError(
                f"iRail returned HTTP {response.status_code} for "
                f"{station} after {MAX_REQUEST_ATTEMPTS} attempts."
            )

        delay_seconds = get_retry_delay_seconds(
            response,
            attempt,
        )

        wait_before_retry(
            station,
            attempt,
            delay_seconds,
            f"HTTP {response.status_code}",
        )

    try:
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
