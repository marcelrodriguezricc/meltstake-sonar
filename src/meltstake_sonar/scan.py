import time
import threading
from datetime import datetime, timezone
from pathlib import Path

from . import utils

_DATA_PATH = None

def _transact_switch(device: str, binary_switch: bytes, dat_path: str | Path, retries: int = 3, retry_delay_s: float = 0.15,) -> bytes:
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

def set_data_path(data_path):
    """Set global data path variable for "scan" module."""

    global _DATA_PATH
    _DATA_PATH = data_path

def scan(switch_cmd: str, device: str, stop_event: threading.Event | None = None):
    """Does an initial dummy ping to get head position, another dummy ping to establish the first recorded step, then 
    """

    # Initialize scan number and return count
    num_scan = 0
    return_count = 0
    
    # Reference operational parameters
    num_sweeps = int(switch_cmd["num_sweeps"])
    utils.append_log(f"Number of sweeps per scan set to {num_sweeps}")

    # Build binary switches
    check_switch = utils.build_binary(switch_cmd, False, True, "CHECK")
    step_switch = utils.build_binary(switch_cmd, False, False, "PING")

    # Send a dummy ping with no step and no data recording to get initial position of head
    utils.append_log(f"Performing dummy ping to get initial head position...")
    read_data = _transact_switch(device, check_switch, dat_path = None)
    response = _parse_response(read_data)
    init_pos = round(response["headpos"], 1)
    utils.append_log(f"Initial head position found at {init_pos}")

    # Send another dummy ping, this will be the first step of each scan
    utils.append_log(f"Starting scan {num_scan}...")
    dat_path = _make_dat_file(num_scan)
    read_data = _transact_switch(device, step_switch, dat_path = None)
    response = _parse_response(read_data)
    pos = round(response["headpos"], 1)

    # Loop indefinitely until termination command is given
    while True:
        if stop_event is not None and stop_event.is_set():
            utils.append_log("Stop requested; ending deployment.")
            return
    
        # Send a switch and record data, get response, record new position
        read_data = _transact_switch(device, step_switch, dat_path)
        response = _parse_response(read_data)
        pos = round(response["headpos"], 1)

        # If the head is at the initial position...
        if pos == init_pos:

            # Record a return
            return_count += 1

            # If the head has returned twice, that is one sweep; if the head has completed the number of sweeps specified in the configuration file, increase the scan number, make a new file for that scan, and reset the number of returns
            if return_count == num_sweeps:
                utils.append_log(f"Finished scan {num_scan}")
                num_scan += 1
                return_count = 0
                dat_path = _make_dat_file(num_scan)
                utils.append_log(f"Starting scan {num_scan}...")