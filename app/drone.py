"""Small synchronous MAVLink controller for the single SITL quadcopter."""

from __future__ import annotations

import threading
import time
from dataclasses import asdict, dataclass
from math import asin, cos, radians, sin, sqrt

from pymavlink import mavutil


class DroneError(RuntimeError):
    """A command could not be safely completed."""


@dataclass
class DroneStatus:
    connected: bool
    mode: str
    armed: bool
    latitude: float | None
    longitude: float | None
    relative_altitude_m: float | None


class DroneController:
    def __init__(self, endpoint: str = "tcp:127.0.0.1:5770") -> None:
        self.endpoint = endpoint
        self.connection: mavutil.mavfile | None = None
        self.target_system: int | None = None
        self.target_component: int | None = None
        self._lock = threading.Lock()

    def connect(self, timeout: float = 20) -> None:
        with self._lock:
            if self.connection is not None:
                return
            self._connect_locked(timeout)

    def close(self) -> None:
        with self._lock:
            if self.connection is not None:
                self.connection.close()
                self.connection = None

    def status(self) -> dict:
        with self._lock:
            return asdict(self._read_status(timeout=5))

    def takeoff(self, altitude_m: float) -> dict:
        with self._lock:
            current = self._read_status(timeout=5)
            if current.armed:
                raise DroneError("Vehicle is already armed; land it before another takeoff")

            try:
                self._set_mode("GUIDED", timeout=10)
                self._command(
                    mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                    [1, 0, 0, 0, 0, 0, 0],
                    timeout=15,
                )
                self._wait_armed(True, timeout=15)
                self._command(
                    mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
                    [0, 0, 0, 0, 0, 0, altitude_m],
                    timeout=10,
                )
                self._wait_altitude(altitude_m, timeout=45)
            except Exception as error:
                details = self._collect_status_text(timeout=3)
                if self._latest_armed():
                    self._send_mode("LAND")
                if isinstance(error, DroneError) and details:
                    raise DroneError(f"{error}; ArduPilot: {'; '.join(details)}") from error
                raise

            result = asdict(self._read_status(timeout=5))
            result["message"] = f"Takeoff completed at about {altitude_m:.1f} m"
            return result

    def land(self) -> dict:
        with self._lock:
            current = self._read_status(timeout=5)
            if not current.armed and (current.relative_altitude_m or 0) < 0.3:
                raise DroneError("Vehicle is already landed and disarmed")

            self._set_mode("LAND", timeout=10)
            self._wait_armed(False, timeout=60)
            result = asdict(self._read_status(timeout=5))
            result["message"] = "Landing completed and vehicle disarmed"
            return result

    def goto(self, latitude: float, longitude: float, altitude_m: float) -> dict:
        with self._lock:
            current = self._read_status(timeout=5)
            if not current.armed or (current.relative_altitude_m or 0) < 0.5:
                raise DroneError("Vehicle must be flying before goto can be used")

            self._set_mode("GUIDED", timeout=10)
            self._send_global_target(latitude, longitude, altitude_m)
            distance_m, altitude_error_m = self._wait_position(
                latitude,
                longitude,
                altitude_m,
                timeout=60,
            )
            result = asdict(self._read_status(timeout=5))
            result["target"] = {
                "latitude": latitude,
                "longitude": longitude,
                "altitude_m": altitude_m,
            }
            result["distance_to_target_m"] = round(distance_m, 2)
            result["altitude_error_m"] = round(altitude_error_m, 2)
            result["message"] = "Target position reached"
            return result

    def rtl(self) -> dict:
        with self._lock:
            current = self._read_status(timeout=5)
            if not current.armed or (current.relative_altitude_m or 0) < 0.5:
                raise DroneError("Vehicle must be flying before RTL can be used")

            self._set_mode("RTL", timeout=10)
            self._wait_armed(False, timeout=120)
            result = asdict(self._read_status(timeout=5))
            result["message"] = "RTL completed; vehicle landed and disarmed"
            return result

    def _read_status(self, timeout: float, reconnect: bool = True) -> DroneStatus:
        connection = self._require_connection()
        self._drain_messages()
        heartbeat = None
        position = None
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and (heartbeat is None or position is None):
            message = connection.recv_match(
                type=["HEARTBEAT", "GLOBAL_POSITION_INT"], blocking=True, timeout=1
            )
            if not self._from_vehicle(message):
                continue
            if message.get_type() == "HEARTBEAT" and self._is_vehicle(message):
                heartbeat = message
            elif message.get_type() == "GLOBAL_POSITION_INT":
                position = message
        if heartbeat is None:
            if reconnect:
                self._reconnect_locked(timeout=20)
                return self._read_status(timeout=timeout, reconnect=False)
            raise DroneError("No heartbeat received from the quadcopter")
        return DroneStatus(
            connected=True,
            mode=mavutil.mode_string_v10(heartbeat),
            armed=bool(
                heartbeat.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
            ),
            latitude=position.lat / 1e7 if position is not None else None,
            longitude=position.lon / 1e7 if position is not None else None,
            relative_altitude_m=position.relative_alt / 1000 if position else None,
        )

    def _drain_messages(self) -> None:
        connection = self._require_connection()
        while connection.recv_match(blocking=False) is not None:
            pass

    def _connect_locked(self, timeout: float) -> None:
        connection = mavutil.mavlink_connection(
            self.endpoint, source_system=254, source_component=191
        )
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            heartbeat = connection.recv_match(
                type="HEARTBEAT", blocking=True, timeout=1
            )
            if self._is_vehicle(heartbeat):
                self.connection = connection
                self.target_system = heartbeat.get_srcSystem()
                self.target_component = heartbeat.get_srcComponent()
                connection.target_system = self.target_system
                connection.target_component = self.target_component
                connection.mav.request_data_stream_send(
                    self.target_system,
                    self.target_component,
                    mavutil.mavlink.MAV_DATA_STREAM_ALL,
                    5,
                    1,
                )
                return
        connection.close()
        raise DroneError("Timed out waiting for the ArduPilot quadcopter")

    def _reconnect_locked(self, timeout: float) -> None:
        if self.connection is not None:
            self.connection.close()
        self.connection = None
        self.target_system = None
        self.target_component = None
        self._connect_locked(timeout)

    def _command(self, command: int, params: list[float], timeout: float) -> None:
        connection = self._require_connection()
        connection.mav.command_long_send(
            self.target_system,
            self.target_component,
            command,
            0,
            *params,
        )
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            ack = connection.recv_match(type="COMMAND_ACK", blocking=True, timeout=1)
            if not self._from_vehicle(ack) or ack.command != command:
                continue
            if ack.result in (
                mavutil.mavlink.MAV_RESULT_ACCEPTED,
                mavutil.mavlink.MAV_RESULT_IN_PROGRESS,
            ):
                return
            raise DroneError(
                f"ArduPilot rejected command {command} with result {ack.result}"
            )
        raise DroneError(f"No acknowledgement for command {command}")

    def _set_mode(self, name: str, timeout: float) -> None:
        wanted = self._send_mode(name)
        connection = self._require_connection()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            heartbeat = connection.recv_match(type="HEARTBEAT", blocking=True, timeout=1)
            if self._is_vehicle(heartbeat) and heartbeat.custom_mode == wanted:
                return
        raise DroneError(f"Timed out changing flight mode to {name}")

    def _send_mode(self, name: str) -> int:
        connection = self._require_connection()
        modes = connection.mode_mapping()
        if name not in modes:
            raise DroneError(f"Flight mode {name} is unavailable")
        wanted = modes[name]
        connection.mav.set_mode_send(
            self.target_system,
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            wanted,
        )
        return wanted

    def _wait_armed(self, armed: bool, timeout: float) -> None:
        connection = self._require_connection()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            heartbeat = connection.recv_match(type="HEARTBEAT", blocking=True, timeout=1)
            if not self._is_vehicle(heartbeat):
                continue
            is_armed = bool(
                heartbeat.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
            )
            if is_armed == armed:
                return
        state = "arm" if armed else "disarm"
        raise DroneError(f"Timed out waiting for vehicle to {state}")

    def _wait_altitude(self, requested_m: float, timeout: float) -> None:
        connection = self._require_connection()
        minimum = max(requested_m - 0.5, requested_m * 0.9)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            position = connection.recv_match(
                type="GLOBAL_POSITION_INT", blocking=True, timeout=1
            )
            if self._from_vehicle(position) and position.relative_alt / 1000 >= minimum:
                return
        raise DroneError(f"Vehicle did not reach {requested_m:.1f} m in time")

    def _send_global_target(
        self,
        latitude: float,
        longitude: float,
        altitude_m: float,
    ) -> None:
        connection = self._require_connection()
        # QGroundControl's map Go To also uses a Guided reposition command. Send
        # the same command type here so this API call cleanly replaces QGC's
        # previous target instead of competing with it as a streamed setpoint.
        connection.mav.command_int_send(
            self.target_system,
            self.target_component,
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
            mavutil.mavlink.MAV_CMD_DO_REPOSITION,
            0,
            0,
            -1,
            0,
            0,
            float("nan"),
            round(latitude * 1e7),
            round(longitude * 1e7),
            altitude_m,
        )

    def _wait_position(
        self,
        latitude: float,
        longitude: float,
        altitude_m: float,
        timeout: float,
    ) -> tuple[float, float]:
        connection = self._require_connection()
        deadline = time.monotonic() + timeout
        next_resend = time.monotonic() + 1
        latest_distance_m: float | None = None
        latest_altitude_error_m: float | None = None
        while time.monotonic() < deadline:
            position = connection.recv_match(
                type="GLOBAL_POSITION_INT", blocking=True, timeout=1
            )
            if self._from_vehicle(position):
                actual_latitude = position.lat / 1e7
                actual_longitude = position.lon / 1e7
                actual_altitude_m = position.relative_alt / 1000
                latest_distance_m = self._distance_m(
                    actual_latitude,
                    actual_longitude,
                    latitude,
                    longitude,
                )
                latest_altitude_error_m = abs(actual_altitude_m - altitude_m)
                if latest_distance_m <= 2 and latest_altitude_error_m <= 0.75:
                    return latest_distance_m, latest_altitude_error_m
            if time.monotonic() >= next_resend:
                self._send_global_target(latitude, longitude, altitude_m)
                next_resend = time.monotonic() + 1

        if latest_distance_m is None or latest_altitude_error_m is None:
            raise DroneError("No position updates received while flying to target")
        raise DroneError(
            "Vehicle did not reach the target in time "
            f"({latest_distance_m:.1f} m away, "
            f"altitude error {latest_altitude_error_m:.1f} m)"
        )

    @staticmethod
    def _distance_m(
        latitude_a: float,
        longitude_a: float,
        latitude_b: float,
        longitude_b: float,
    ) -> float:
        radius_m = 6_371_000
        latitude_delta = radians(latitude_b - latitude_a)
        longitude_delta = radians(longitude_b - longitude_a)
        haversine = (
            sin(latitude_delta / 2) ** 2
            + cos(radians(latitude_a))
            * cos(radians(latitude_b))
            * sin(longitude_delta / 2) ** 2
        )
        return 2 * radius_m * asin(sqrt(haversine))

    def _latest_armed(self) -> bool:
        connection = self._require_connection()
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            heartbeat = connection.recv_match(type="HEARTBEAT", blocking=True, timeout=0.5)
            if self._is_vehicle(heartbeat):
                return bool(
                    heartbeat.base_mode
                    & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
                )
        return False

    def _collect_status_text(self, timeout: float) -> list[str]:
        connection = self._require_connection()
        messages: list[str] = []
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            status = connection.recv_match(type="STATUSTEXT", blocking=True, timeout=0.5)
            if not self._from_vehicle(status):
                continue
            text = status.text.strip()
            if text and text not in messages:
                messages.append(text)
        return messages

    def _require_connection(self) -> mavutil.mavfile:
        if self.connection is None:
            raise DroneError("Drone connection is not ready")
        return self.connection

    def _from_vehicle(self, message) -> bool:
        return message is not None and message.get_srcSystem() == self.target_system

    @staticmethod
    def _is_vehicle(message) -> bool:
        return (
            message is not None
            and message.get_type() == "HEARTBEAT"
            and message.autopilot == mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA
            and message.type == mavutil.mavlink.MAV_TYPE_QUADROTOR
        )
