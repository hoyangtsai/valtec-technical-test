#!/usr/bin/env python3
"""Run the documented Valtec API acceptance flow from the host Mac."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class DemoError(RuntimeError):
    """The acceptance flow could not continue safely."""


def request_json(base_url: str, method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if body is not None else {}
    request = Request(f"{base_url}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=150) as response:
            result = json.load(response)
    except HTTPError as error:
        details = error.read().decode(errors="replace")
        raise DemoError(f"{method} {path} returned HTTP {error.code}: {details}") from error
    except URLError as error:
        raise DemoError(f"Cannot reach {base_url}: {error.reason}") from error

    print(f"\n{method} {path} -> HTTP 200")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


def require_number(status: dict[str, Any], field: str) -> float:
    value = status.get(field)
    if not isinstance(value, (int, float)):
        raise DemoError(f"Status did not contain a numeric {field}: {value!r}")
    return float(value)


def pause(message: str) -> None:
    input(f"\n{message}\nPress Enter to continue...")


def run(base_url: str, skip_qgc: bool) -> None:
    print("Valtec simulated-drone API demonstration")
    print(f"API: {base_url}")
    pause("Confirm Docker is healthy and QGroundControl shows Ready.")

    initial = request_json(base_url, "GET", "/status")
    if initial.get("armed"):
        raise DemoError("Vehicle is already armed. Land it before starting the demo.")

    latitude = require_number(initial, "latitude")
    longitude = require_number(initial, "longitude")
    target_latitude = latitude + (10 / 111_111)

    pause("Step 1: API takeoff to 3 m. Keep QGroundControl visible.")
    request_json(base_url, "POST", "/takeoff", {"altitude_m": 3})

    pause("Step 2: API land at the current position.")
    request_json(base_url, "POST", "/land")

    pause("Step 3: API takeoff to 3 m again.")
    request_json(base_url, "POST", "/takeoff", {"altitude_m": 3})

    if not skip_qgc:
        before_qgc = request_json(base_url, "GET", "/status")
        print("\nPosition before manual QGC Go To:")
        print(f"  latitude={before_qgc.get('latitude')}, longitude={before_qgc.get('longitude')}")
        pause(
            "In QGroundControl Fly view, use Go To for a nearby point (about 10-30 m). "
            "Wait until movement stops."
        )
        after_qgc = request_json(base_url, "GET", "/status")
        print("\nPosition read by the API after QGC Go To:")
        print(f"  latitude={after_qgc.get('latitude')}, longitude={after_qgc.get('longitude')}")

    pause("Step 5: API goto about 10 m north of the launch point at 3 m altitude.")
    request_json(
        base_url,
        "POST",
        "/goto",
        {
            "latitude": round(target_latitude, 7),
            "longitude": round(longitude, 7),
            "altitude_m": 3,
        },
    )

    pause("Step 6: API RTL. The vehicle will return, land, and disarm.")
    request_json(base_url, "POST", "/rtl")

    final = request_json(base_url, "GET", "/status")
    if final.get("armed") or abs(require_number(final, "relative_altitude_m")) >= 0.3:
        raise DemoError("Final state is not safely landed and disarmed.")

    print("\nPASS: complete flow finished; the simulated vehicle is landed and disarmed.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the exact takeoff, land, QGC Go To, goto, and RTL acceptance order."
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="FastAPI base URL (default: %(default)s)",
    )
    parser.add_argument(
        "--skip-qgc",
        action="store_true",
        help="Skip the pause for a manual QGroundControl Go To command",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        run(args.base_url.rstrip("/"), args.skip_qgc)
    except (DemoError, KeyboardInterrupt) as error:
        print(f"\nSTOPPED: {error}", file=sys.stderr)
        print("Check QGroundControl and use POST /land if the vehicle is still flying.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
