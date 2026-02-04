import time
import threading
from pathlib import Path
from typing import Any

from . import utils

def _transact_switch(device: Any, binary_switch: bytes, data_path: str | Path | None, log_path: Path | None = None, retries: int = 3, retry_delay_s: float = 0.15,) -> bytes:
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
            utils.append_log(log_path, f"Switch transaction attempt {attempt}: failed to reset buffers: {e}")

        # Write switch command
        try:
            sent_count = device.write(binary_switch)
            device.flush()
        except Exception as e:
            utils.append_log(log_path, f"Switch transaction attempt {attempt}: failed to send command: {e}")
            if attempt <= retries:
                time.sleep(retry_delay_s)
                continue
            return b""

        # Validate switch length
        if sent_count != len(binary_switch):
            utils.append_log(
                log_path,
                f"Switch transaction attempt {attempt}: short write (sent {sent_count}, expected {len(binary_switch)})",
            )
            if attempt <= retries:
                time.sleep(retry_delay_s)
                continue
            return b""

        # Read sonar response
        try:
            read_data = device.read_until(b"\xfc")
        except Exception as e:
            utils.append_log(log_path, f"Switch transaction attempt {attempt}: failed to read response: {e}")
            if attempt <= retries:
                time.sleep(retry_delay_s)
                continue
            return b""

        # Validate response terminator
        if not read_data or not read_data.endswith(b"\xfc"):
            utils.append_log(
                log_path,
                f"Switch transaction attempt {attempt}: bad/unterminated response (len={len(read_data)})",
            )
            if attempt <= retries:
                time.sleep(retry_delay_s)
                continue
            return b""

        # Write raw response to data file
        if data_path:
            try:
                with open(data_path, "ab") as file:
                    file.write(read_data)
            except Exception as e:
                utils.append_log(log_path, f"Failed to write raw data to {data_path}: {e}")

        return read_data

    return b""

def _parse_response(sonar_data: bytes, log_path: Path | None = None) -> dict:
    """Convert sonar response into dictionary with engineering units."""

    # Initialize response as an empty dictionary
    response: dict = {}

    # If the length of the raw sonar response is less than 12 bytes, write an error to log and flag a bad parse
    if len(sonar_data) <= 12:
        utils.append_log(log_path, f"Parse error: response too short (len={len(sonar_data)})")
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
        utils.append_log(log_path, f"Parse error: failed to parse response (len={len(sonar_data)}): {e}")
        return {}
    
def _make_data_file(num_deploy: int, num_scan: int, log_path: Path | None = None) -> str:
    """Make .dat file to be appended with raw sonar data."""

    # Make .dat file to store raw data (one per scan)
    try:
        data_path = utils.make_file(Path("data") / f"deployment_{num_deploy}", f"scan_{num_scan}.dat")
    except Exception:
        utils.append_log(log_path, f"Failed to create data file at {data_path}")
        raise
    else:
        utils.append_log(log_path, f"Data file created at {data_path}")

    return data_path

def scan(num_deploy: int, switch_cmd: dict[str, Any], device: str, log_path: Path | None = None, stop_event: threading.Event | None = None):
    """First performs an initial ping without recording to get starting position 
    
    Args:
        num_deploy: Deployment number string for file naming, passed in as a CLI argument (from `parse_args()).
        binary_switch: Raw switch command compiled from configuration settings as bytes (from `build_binary()`).
        switch_cmd: Switch command configuration parameters parsed into a dictionary (from `parse_config()`).
        device: Path to device as a string (from `init_serial()`).
        log_path: The path to the log file as a string (from `create_log_file()`). If None, nothing is written.
    """

    # Initialize scan number and return count
    num_scan = 0
    return_count = 0
    
    # Reference operational parameters
    num_sweeps = int(switch_cmd["num_sweeps"])
    utils.append_log(log_path, f"Number of sweeps per scan set to {num_sweeps}")

    # Build binary switches
    check_switch = utils.build_binary(switch_cmd, False, True, log_path, "CHECK")
    step_switch = utils.build_binary(switch_cmd, False, False, log_path, "PING")

    # Send a dummy ping with no step and no data recording to get initial position of head
    utils.append_log(log_path, f"Performing dummy ping to get initial head position...")
    read_data = _transact_switch(device, check_switch, data_path = None, log_path = log_path)
    response = _parse_response(read_data, log_path)
    init_pos = round(response["headpos"], 1)
    utils.append_log(log_path, f"Initial head position found at {init_pos}")

    # Send a switch and record data, outside of loop so pos is not equal to init pos on first good step
    utils.append_log(log_path, f"Starting scan {num_scan}...")
    data_path = _make_data_file(num_deploy, num_scan, log_path)
    read_data = _transact_switch(device, step_switch, data_path, log_path = log_path)
    response = _parse_response(read_data, log_path)
    pos = round(response["headpos"], 1)

    # Loop indefinitely until termination command is given
    while True:
        if stop_event is not None and stop_event.is_set():
            utils.append_log(log_path, "Stop requested; ending deployment.")
            return
    
        # Send a switch and record data, get response, record new position
        read_data = _transact_switch(device, step_switch, data_path = None, log_path = log_path)
        response = _parse_response(read_data, log_path)
        pos = round(response["headpos"], 1)

        # If the head is at the initial position...
        if pos == init_pos:

            # Record a return
            return_count += 1

            # If the head has returned twice, that is one sweep; if the head has completed the number of sweeps specified in the configuration file, increase the scan number, make a new file for that scan, and reset the number of returns
            if return_count == (num_sweeps * 2):
                num_scan += 1
                utils.append_log(log_path, f"Finished scan {num_scan}")
                data_path = _make_data_file(num_deploy, num_scan, log_path)
                return_count = 0
                utils.append_log(log_path, f"Starting scan {num_scan}...")