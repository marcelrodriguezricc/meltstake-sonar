import time
import threading
from datetime import datetime, timezone
from pathlib import Path

from . import utils

_DATA_PATH = None

def _transact_switch(device: str, binary_switch: bytes, dat_path: str | Path, retries: int = 5, retry_delay_s: float = 0.25,) -> bytes:
    """Write one switch command to sonar device and read response.

    Retries on:
      - Buffer reset errors (non-fatal, still continues)
      - Send/write errors
      - Short writes
      - Read errors
      - Empty or unterminated responses (missing 0xFC)

    Returns b"" if all attempts fail.
    """

    # Attempt switch transaction "attempt" number of times if failed
    for attempt in range(1, retries + 2):
        
        # Clear buffers
        try:
            device.reset_input_buffer()
            device.reset_output_buffer()
        except Exception as e:
            utils.append_log(f"Switch transaction attempt {attempt}: failed to reset buffers: {e}")

        # Write switch command
        try:
            sent_count = device.write(binary_switch)
            device.flush()
        except Exception as e:
            utils.append_log(f"Switch transaction attempt {attempt}: failed to send command: {e}")
            if attempt <= retries:
                time.sleep(retry_delay_s)
                continue
            return b""

        # Validate switch length
        if sent_count != len(binary_switch):
            utils.append_log(f"Switch transaction attempt {attempt}: short write (sent {sent_count}, expected {len(binary_switch)})",)
            if attempt <= retries:
                time.sleep(retry_delay_s)
                continue
            return b""

        # Read sonar response
        try:
            read_data = device.read_until(b"\xfc")
            print(read_data)
        except Exception as e:
            utils.append_log(f"Switch transaction attempt {attempt}: failed to read response: {e}")
            if attempt <= retries:
                time.sleep(retry_delay_s)
                continue
            return b""

        # Validate response terminator
        if not read_data or not read_data.endswith(b"\xfc"):
            utils.append_log(f"Switch transaction attempt {attempt}: bad/unterminated response (len={len(read_data)})",)
            if attempt <= retries:
                time.sleep(retry_delay_s)
                continue
            return b""

        # Write raw response to data file
        if dat_path:
            try:
                with open(dat_path, "ab") as file:
                    file.write(read_data)
            except Exception as e:
                utils.append_log(f"Failed to write raw data to {dat_path}: {e}")

        return read_data

    return b""

def _parse_response(sonar_data: bytes) -> dict:
    """Convert sonar response into dictionary with engineering units."""

    # Initialize response as an empty dictionary
    response: dict = {}

    # If the length of the raw sonar response is less than 12 bytes, write an error to log and flag a bad parse
    if len(sonar_data) <= 12:
        utils.append_log(f"Parse error: response too short (len={len(sonar_data)})")
        return {}
    
    # Convert raw sonar response to engineering units and pack in response object
    try:
        response["header"] = bytes(sonar_data[0:3]).decode("utf-8", errors="strict")
        response["headid"] = sonar_data[3]
        response["serialstatus"] = sonar_data[4]
        if response["header"] != "IOX":
            response["stepdirection"] = 1 if sonar_data[6] & 64 else 0
            response["headpos"] = (((sonar_data[6] & 63) << 7 | (sonar_data[5] & 127)) - 600) * 0.3
            response["comment"] = (
                "Computing head position"
                + str(response["headpos"])
                + " from byte 5="
                + str(sonar_data[5])
                + " and 6="
                + str(sonar_data[6])
            )
            response["range"] = sonar_data[7]
            response["profilerange"] = (sonar_data[9] << 7) | (sonar_data[8] & 127)
        response["databytes"] = (sonar_data[11] << 7) | (sonar_data[10] & 127)
        data = ""
        for val in sonar_data[12:-1]:
            data += "{0:02x}".format(val)
        response["data"] = data

        return response
    
    except Exception as e:
        utils.append_log(f"Parse error: failed to parse response (len={len(sonar_data)}): {e}")
        return {}
    
def _make_dat_file(num_scan: int) -> str:
    """Make .dat file to be appended with raw sonar data."""

    # Make .dat file to store raw data (one per scan)
    try:
        file = f"sonarScan{num_scan}.dat"
        data_path = utils.make_file(file)
    except Exception:
        utils.append_log(f"Failed to create data file at {data_path}")
        raise
    else:
        utils.append_log( f"Data file created at {data_path}")

    # Write data file name to run index csv
    try:
        utc_dt = datetime.now(timezone.utc)
        timestamp = utc_dt.strftime("%Y-%m-%d %H:%M:%S")
        csv_path = f"{_DATA_PATH}/RunIndex.csv"
        with open(csv_path, "a") as outfile:
                    outfile.write(timestamp + "," + "scan" + "," + file + "\n")
    except Exception:
        utils.append_log(f"Failed to append {file} to RunIndex.csv at {csv_path}")
        raise
    else:
        utils.append_log(f"{file} appended to RunIndex.csv at {csv_path}")

    return data_path

def _scan_extents(switch_cmd: dict) -> tuple[float, float, float]:
    """Calculates and outputs centerline and low/high angular extents of the sonar's sweep in degrees.
    """

    centerline = -180.0 + 3.0 * switch_cmd["train_angle"]
    sector = 3.0 * switch_cmd["sector_width"]
    half = sector / 2.0
    return centerline, centerline - half, centerline + half

def _wrap180(deg: float) -> float:
    """Wraparound logic for -180 to 180 sonar frame."""

    return (deg + 180.0) % 360.0 - 180.0

def _in_sector(pos: float, centerline: float, sector: float) -> bool:
    """True if pos is within the sweep, handling the ±180 wraparound seam."""

    half = sector / 2.0
    delta = abs(_wrap180(pos - centerline))
    return delta <= half

def _read_validate(device, switch: bytes, dat_path, retries: int = 3,
                retry_delay_s: float = 0.15) -> dict | None:
    """Transact a non-stepping switch and parse, retrying the pair until a response returns or attempts are exhausted.
    """
    for attempt in range(1, retries + 2):
        response = _parse_response(_transact_switch(device, switch, dat_path))
        if response and "headpos" in response:
            return response
        utils.append_log(
            f"Read attempt {attempt}: unusable response "
            f"(keys: {list(response.keys()) or 'none'}); retrying."
        )
        time.sleep(retry_delay_s)
    utils.append_log(f"Read failed after {retries + 1} attempts.")
    return None


def _step_and_read(device, step_switch: bytes, check_switch: bytes, dat_path,
                   retries: int = 3, retry_delay_s: float = 0.15) -> dict | None:
    """Send a stepping and return its parsed response.
    """
    response = _parse_response(_transact_switch(device, step_switch, dat_path))
    if response and "headpos" in response:
        return response
    utils.append_log("Stepping ping unparseable; attempting to recover position.")
    return _read_validate(device, check_switch, None, retries, retry_delay_s)

def set_data_path(data_path):
    """Set global data path variable for "scan" module."""

    global _DATA_PATH
    _DATA_PATH = data_path

def scan(switch_cmd: dict, device: str, stop_event: threading.Event | None = None):
    """Does an initial dummy ping to get head position, another dummy ping to establish the first recorded step, then 
    """

    # Initialize scan number and return count
    num_scan = 0
    return_count = 0

    # Build binary switches
    check_switch = utils.build_binary(switch_cmd, False, True, "CHECK")
    step_switch = utils.build_binary(switch_cmd, False, False, "PING")

    # Determine position tolerance from step size to harden init_pos and pos matching from floating point precision discrepancies
    step_size = switch_cmd["step_size"]
    deg_per_step = step_size * 0.3
    pos_tolerance = deg_per_step / 2
    if deg_per_step == 0:
        utils.append_log("step_size is 0; head cannot advance. Ending deployment.")
        return

    # Determine extents of scan
    centerline, low_range, high_range = _scan_extents(switch_cmd)
    sector = 3.0 * switch_cmd["sector_width"]

    # Send a dummy ping with no step and no data recording to get initial position of head
    utils.append_log("Performing dummy ping to get initial head position...")
    response = _read_validate(device, check_switch, None)
    if response is None:
        utils.append_log("Could not read initial head position; ending deployment.")
        return
    init_pos = round(response["headpos"], 1)
    utils.append_log(f"Initial head position found at {init_pos}")

    # Bound the seek so a frame mismatch or empty sector aborts instead of looping forever
    max_seek_steps = int(360 / deg_per_step) + 1 if deg_per_step else 0

    # If the head starts outside the sweep, step it in until it lands within the extents
    seek = 0
    while not _in_sector(init_pos, centerline, sector):
        if stop_event is not None and stop_event.is_set():
            utils.append_log("Stop requested during initial-position seek; ending deployment.")
            return
        if seek >= max_seek_steps:
            utils.append_log(
                f"Head still out of range ({init_pos}) after {seek} steps; "
                f"check that headpos and extents ({low_range} - {high_range}) share a frame. Aborting."
            )
            return
        
        # Advance one step without recording data, then re-read position without stepping
        _transact_switch(device, step_switch, dat_path=None)
        response = _read_validate(device, check_switch, None)
        if response is None:
            utils.append_log("Could not read head position during seek; ending deployment.")
            return
        init_pos = round(response["headpos"], 1)
        seek += 1

    utils.append_log(f"Initial head position in range at {init_pos}")

    # Send another dummy ping, this position will be the first step of each scan
    utils.append_log(f"Starting scan {num_scan}...")
    dat_path = _make_dat_file(num_scan)
    response = _step_and_read(device, step_switch, check_switch, dat_path=None)
    if response is None:
        utils.append_log("Could not read first step; ending deployment.")
        return
    pos = round(response["headpos"], 1)
    in_initial_zone = abs(pos - init_pos) < pos_tolerance

    # Loop indefinitely until termination command is given
    while True:
        if stop_event is not None and stop_event.is_set():
            utils.append_log("Stop requested; ending deployment.")
            return
    
        # Send a switch and record data, get response, record new position
        response = _step_and_read(device, step_switch, check_switch, dat_path)
        if response is None:
            utils.append_log("Could not recover head position; ending deployment.")
            return
        pos = round(response["headpos"], 1)

        # Rising edge check so entering the range of the initial zone counts once, removing double-counting recovery re-reads
        at_initial = deg_per_step > 0 and abs(pos - init_pos) < pos_tolerance
        

        # If the head is at the initial position...
        if at_initial and not in_initial_zone:

            # Record a return
            return_count += 1
            utils.append_log(
                f"Head at initial position — init {init_pos}, current {pos}, returns {return_count}"
            )

            # If the head has returned to the initial position twice, start a break the scan and start a new scan
            if return_count == 2:
                utils.append_log(f"Finished scan {num_scan}")
                num_scan += 1
                return_count = 0
                dat_path = _make_dat_file(num_scan)
                utils.append_log(f"Starting scan {num_scan}...")

        in_initial_zone = at_initial