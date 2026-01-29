from . import utils
from pathlib import Path
from typing import Any

def _transact_switch(device: str, binary_switch: bytes, data_path: str | Path | None, log_path: Path | None = None, step: int = 0,) -> tuple[bytes, bool]:
    """Write one switch command and read response to sonar device."""

    # Initialize success / fail variable 
    ok = True

    # Clear read buffer
    try:
        device.reset_input_buffer()
    except Exception as e:
        ok = False
        utils.append_log(log_path, f"Step {step}: failed to reset input buffer: {e}")

    # Write switch command to sonar
    try:
        sent_count = device.write(binary_switch)
        device.flush()
    except Exception as e:
        ok = False
        utils.append_log(log_path, f"Step {step}: failed to send command: {e}")
        return b"", False
    
    if sent_count != len(binary_switch):
        ok = False
        utils.append_log(log_path, f"Step {step}: sent {sent_count} bytes, expected {len(binary_switch)}")

    # Read sonar response
    try:
        read_data = device.read_until(b"\xfc")
    except Exception as e:
        ok = False
        utils.append_log(log_path, f"Step {step}: failed to read response: {e}")
        return b"", False

    # Ensure we received a response and that it ended with the correct terminator byte
    if not read_data or not read_data.endswith(b"\xfc"):
        ok = False
        utils.append_log(log_path, f"Step {step}: bad/unterminated response (len={len(read_data)})")

    # Write raw response to data file
    if data_path:
        try:
            with open(data_path, "ab") as file:
                file.write(read_data)
        except Exception as e:
            ok = False
            utils.append_log(log_path, f"Step {step}: failed to write raw data to {data_path}: {e}")

    return read_data, ok

def _parse_response(sonar_data: bytes, log_path: Path | None = None) -> tuple[dict, bool]:
    """Convert sonar response into dictionary with engineering units."""

    # Initialize response as an empty dictionary
    response: dict = {}

    # If the length of the raw sonar response is less than 12 bytes, write an error to log and flag a bad parse
    if len(sonar_data) <= 12:
        utils.append_log(log_path, f"Parse error: response too short (len={len(sonar_data)})")
        return {}, False

    # Convert raw sonar response to engineering units and pack in response object
    try:
        response["header"] = bytes(sonar_data[0:3]).decode("utf-8", errors="strict")
        response["headid"] = sonar_data[3]
        response["serialstatus"] = sonar_data[4]
        if response["header"] != "IOX":
            response["stepdirection"] = 1 if sonar_data[6] & 64 else 0
            response["headpos"] = (((sonar_data[6] & 63) << 7 | (sonar_data[5] & 127)) - 600) * 0.3
            response["comment"] = (
                "Computing head position "
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

        return response, True
    
    except Exception as e:
        utils.append_log(log_path, f"Parse error: failed to parse response (len={len(sonar_data)}): {e}")
        return {}, False
    
def _make_data_file(deployment: int, num_scan: int, log_path: Path | None = None) -> str:
    """Make .dat file to be appended with raw sonar data."""

    # Make .dat file to store raw data (one per scan)
    try:
        data_path = utils.make_file(Path("data") / f"deployment_{deployment}", f"scan_{num_scan}.dat")
    except Exception:
        utils.append_log(log_path, f"Failed to create data file at {data_path}")
        raise
    else:
        utils.append_log(log_path, f"Data file created at {data_path}")

    return data_path

def scan_sector(deployment: int, ops: dict[str, Any], switch_cmd: dict[str, Any], device: str, binary_switch: bytes, num_scan: int, log_path: Path | None = None):
    """Run a sonar scan and write raw data to .dat file (one per scan).
    
    Args:
        deployment: Deployment number string for file naming, passed in as a CLI argument (from `parse_args()).
        ops: Operational configuration parameters parsed into a dictionary (from `parse_config()`).
        switch_cmd: Switch command configuration parameters parsed into a dictionary (from `parse_config()`).
        device: Path to device as a string (from `init_serial()`).
        command: Raw switch command compiled from configuration settings as bytes (from `build_binary()`).
        num_scan: The number of the scan currently being executed as an integer.
        log_path: The path to the log file as a string (from `create_log_file()`). If None, nothing is written.

    Writes number of steps, successful / unsuccessful scans, and path to .dat file to log.
    """

    # Create file for raw sonar data
    data_path = _make_data_file(deployment, num_scan, log_path)

    # Determine number of individual steps needed for a single sweep
    num_steps = int(float(switch_cmd["sector_width"]) / (float(switch_cmd["step_size"]) * 0.3))

    # Reference operational parameters
    num_sweeps = int(ops["num_sweeps"])
    direction = int(ops["direction"])

    # Initialize variables for number of step successes / failures in a scan
    success = 0
    failure = 0

    # Write the beginning of scan to log
    utils.append_log(log_path, f"Starting Scan {num_scan}")

    # For each sweep...
    for i in range(num_sweeps):
        if i == 1:
            # TODO: GET HEAD POSITION, IF NOT AT START RETURN TO STARTING POSITION
            for j in range(num_steps):
                sonar_data, transaction_ok = _transact_switch(device, binary_switch, data_path, log_path, j,)
                response, parse_ok = _parse_response(sonar_data=sonar_data, log_path=log_path)
                ok = transaction_ok and parse_ok 
                if ok:
                    success += 1
                else:
                    failure += 1
                # TODO: REFERENCE RESPONSE HEAD POSITION AND TERMINATE SCAN WHEN END OF SECTOR IS REACHED
        #else:
            # TODO: IF DIRECTIONALITY 0 (BIDIRECTIONAL), IF NOT AT START RETURN TO STARTING POSITION, SCAN UNTIL SECTOR WIDTH IS REACHED, THEN SCAN AGAIN BACK TO STARTING POSITION.
            # TODO: IF DIRECTIONALITY 1 (UNIDIRECTIONAL), IF NOT AT START RETURN TO STARTING POSITION, SCAN UNTIL SECTOR WIDTH IS REACHED, RETURN TO STARTING POSITION AGAIN, SCAN AGAIN.

    # Write scan information to log
    utils.append_log(
        log_path,
        f"Scan {num_scan} complete: steps={num_steps}, successful={success}, unsuccessful={failure}, data_file={data_path}",
    )