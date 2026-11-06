"""Verify telemetry through the router without arming or moving the vehicle."""
import argparse
import json
import time

from pymavlink import mavutil

parser = argparse.ArgumentParser()
parser.add_argument("--heartbeat-only", action="store_true")
args = parser.parse_args()
connection = mavutil.mavlink_connection("tcp:127.0.0.1:5770", source_system=253)
try:
    heartbeat = None
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        candidate = connection.recv_match(type="HEARTBEAT", blocking=True, timeout=1)
        if (candidate is not None
                and candidate.autopilot == mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA
                and candidate.type == mavutil.mavlink.MAV_TYPE_QUADROTOR):
            heartbeat = candidate
            break
    if heartbeat is None:
        raise SystemExit("No heartbeat from the simulator through MAVLink-router")
    result = {"system_id": heartbeat.get_srcSystem(),
              "vehicle_type": heartbeat.type,
              "autopilot": heartbeat.autopilot,
              "mode": mavutil.mode_string_v10(heartbeat),
              "armed": bool(heartbeat.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)}
    if not args.heartbeat_only:
        connection.mav.request_data_stream_send(
            heartbeat.get_srcSystem(), heartbeat.get_srcComponent(),
            mavutil.mavlink.MAV_DATA_STREAM_ALL, 2, 1)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            message = connection.recv_match(type="GLOBAL_POSITION_INT", blocking=True, timeout=1)
            if (message and message.get_srcSystem() == heartbeat.get_srcSystem()
                    and message.lat and message.lon):
                result.update(latitude=message.lat / 1e7, longitude=message.lon / 1e7,
                              relative_altitude_m=message.relative_alt / 1000)
                break
        else:
            raise SystemExit("Heartbeat received, but no valid position within 10 seconds")
    print(json.dumps(result, indent=2))
finally:
    connection.close()
