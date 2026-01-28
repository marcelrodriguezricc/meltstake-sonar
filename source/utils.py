# Import libraries
import os
from pathlib import Path
import serial
from serial.tools import list_ports
import tomllib
import time

# ----- MISC INTERNAL HELPERS -----

def _utc_time_part() -> str:
    """Return the current UTC time as HH:MM:SS."""

    # Get UTC time in human-readable format (hours.minutes.seconds)
    my_time = time.strftime("%H:%M:%S", time.gmtime())

    return my_time

def _append_log(log_path: Path, line: str) -> None:
    """Append a line to the log file with a UTC time prefix.

    Args:
        log_path: Path to the log file.
        line: Message to append (a trailing newline is added automatically).
    """

    # End function if no path is specified
    if log_path is None:
        return
    
    # UTC time to prepend each log entry
    prefix = _utc_time_part()

    # Open file and append line
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"{prefix}: {line.rstrip()}\n")

def _make_file(dir: str | Path, filename: str) -> Path:
    """Create a path under `dir`, creating the directory if needed.

    Args:
        dir: Directory where file will be saved, creates one if none exists
        filenname: Name of file with suffix
    """

    # Prepend user home directory
    out_dir = Path(dir).expanduser()

    # Make directory if it doesn't already exist
    out_dir.mkdir(parents=True, exist_ok=True)

    # Set file path with directory/filename
    out_path = out_dir / filename

    # Create file
    out_path.touch(exist_ok=True)

    return out_path

# ----- INITIALIZATION INTERNAL HELPERS -----

def _load_config(log_path: Path | None) -> dict:
    """Load config.toml (in the same folder as this file).

    Args:
        log_path: Path to log for error/success logging.

    Returns:
        Parsed TOML configuration as a dictionary.

    Raises:
        FileNotFoundError: If config.toml does not exist.
        tomllib.TOMLDecodeError: If config.toml is not valid TOML.
        OSError: If the file cannot be read due to an OS-level error.
    """

    # Set path to configuration file, hardcoded to config.toml in the same directory as utils.py
    cfg_path = Path(__file__).with_name("config.toml")

    # Load the configuration as a Python dictionary
    try:
        with cfg_path.open("rb") as f:
            cfg = tomllib.load(f)
    except (FileNotFoundError, tomllib.TOMLDecodeError, OSError) as e:
        _append_log(log_path, f"Failed to load configuration file at {cfg_path}: {e}")
        raise
    else:
        _append_log(log_path, f"Configuration file loaded: {cfg_path}")

    return cfg

# ----- INITIALIZATION PUBLIC FUNCTIONS -----

def create_log_file() -> Path:
    """Create ./logs/<YYYY-MM-DD_HH-MM-SS>.log (UTC) and write an init line."""

    # Get UTC datetime
    datetime = time.strftime("%Y-%m-%d_%H.%M.%S", time.gmtime())

    # Create a log file at directory "logs" with datetime.log as file name
    log_path = _make_file("logs", f"{datetime}.log")
    _append_log(log_path, "Melt Stake 881A Sonar deployment log initialized")

    return log_path

def parse_config(log_path: Path | None) -> tuple[dict,dict,dict]:
    """Parse config.toml and return the sonar switch parameters as a dict.

    Args:
        log_path: Path to the log file. If None, nothing is written.

    Returns:
        Dictionary of switch parameters used to build the command.

    Raises:
        KeyError: If required config keys are missing (e.g., [switch] or fields within it).
        TypeError: If the loaded config structure is not subscriptable as expected.
        FileNotFoundError: If config.toml does not exist.
        tomllib.TOMLDecodeError: If config.toml is not valid TOML.
        OSError: If the file cannot be read due to an OS-level error.
    """

    # Load the configuration file as a dictionary
    cfg = _load_config(log_path)
    
    # Separate system and switch settings
    try:
        connection = cfg["connection"]
        ops = cfg["ops"]
        switch_cmd = cfg["switch_cmd"]
    except (KeyError, TypeError) as e:
        _append_log(log_path, f"Failed to parse configuration from config.toml: {e}")
        raise
    else:
        _append_log(log_path, f"Configuration loaded from config.toml")

    port = connection.get("port")
    if port == "" or port is None:
        connection["port"] = None
    device_name = connection.get("device_name")
    if device_name == "" or device_name is None:
        connection["device_name"] = None

    return connection, ops, switch_cmd

def auto_detect_port(device_name: str) -> str | None:
    """Automatic serial port detection."""

    # Check for name in names and descriptions for each port list of serial ports
    for p in list_ports.comports():
        if device_name in (p.device or "").lower() or device_name in (p.description or "").lower():
            return p.device
        
    return None

def init_serial(connection=dict, baud: int = 115200, timeout: float = 10.0, log_path: str | None = None) -> serial.Serial:
    """Initialize and return a serial connection.

    Args:
        connection: Dictionary containing port and device name strings as set in configuration file (from `parse_config()`).
        timeout: Read/write timeout in seconds.
        log_path: Path to log file; if None, nothing is written.

    Returns:
        An opened `serial.Serial` instance.

    Raises:
        serial.SerialException: If no port is available or the port cannot be opened.
        OSError: If the OS refuses access to the device (permissions/in-use).
    """
    
    port = connection["port"]
    device_name = connection["device_name"]

    if port is None:
        port = auto_detect_port(device_name)

    if not port:
        _append_log(log_path, "Melt Stake 881A Sonar deployment log initialized")
        
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baud,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout,
            write_timeout=timeout,
        )
    except (serial.SerialException, OSError) as e:
        _append_log(log_path, f"Failed to open serial port {port!r} at {baud} baud: {e}")
        raise
    else:
        _append_log(log_path, f"Serial port opened: {port!r} @ {baud} baud")

    
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    return ser

def build_binary(switch_cmd: dict, calibration: bool = False, log_path: str | None = None):
    """Build the 27-byte 881A sonar switch command from switch_cmd dictionary.

    This constructs a fixed-length `bytearray(27)` using values from `switch_cmd`
    and optionally enables calibration.

    Args:
        switch_cmd: Dictionary of switch parameters (from `parse_config()`).
        calibration: If True, sets the calibration flag byte in the command.
        log_path: Path to the log file. If None, nothing is written.

    Returns:
        A 27-byte command payload as a `bytearray`.

    Raises:
        KeyError: If `switch_cmd` is missing a required key.
        TypeError: If `switch_cmd` is not subscriptable or contains incompatible value types.
    """
    
    # Length of byte command payload
    command=bytearray(27)

    # Calibration flag
    calibrate = int(bool(calibration))

    # Compile byte command payload based on switch command configuration settings
    try:
        command[0] = 0xFE                        # Switch data header
        command[1] = 0x44                        # Switch data header
        command[2] = 16                          # Head ID
        command[3] = switch_cmd["max_range"]     # Range
        command[4] = 0                           # Reserved, must be 0
        command[5] = 0                           # Rev / hold
        command[6] = 0x43                        # Master / Slave (always slave)
        command[7] = 0                           # Reserved, must be 0
        command[8]  = switch_cmd["start_gain"]   # Start Gain
        command[9]  = switch_cmd["logf"]         # Logf
        command[10] = switch_cmd["absorption"]   # Absorption
        command[11] = switch_cmd["train_angle"]  # Train angle
        command[12] = switch_cmd["sector_width"] # Sector width
        command[13] = switch_cmd["step_size"]    # Step size
        command[14] = switch_cmd["pulse_length"] # Pulse length
        command[15] = 0                          # Profile Minimum Range (reserved/unused here)
        command[16] = 0                          # Reserved, must be 0
        command[17] = 0                          # Reserved, must be 0
        command[18] = 0                          # Reserved, must be 0
        command[19] = switch_cmd["data_points"]  # Data points
        command[20] = 8                          # Resolution (8-bit)
        command[21] = 0x06                       # 115200
        command[22] = 0                          # 0 - off, 1 = on
        command[23] = calibrate                  # calibrate, 0 = off, 1 = on
        command[24] = 1                          # Switch delay
        command[25] = switch_cmd["freq"]         # Frequency
        command[26] = 0xFD                       # Termination byte
    except (KeyError, TypeError) as e:
        _append_log(log_path, f"Failed to build binary command from switch_cmd: {e}")
        raise
    else:
        _append_log(log_path, f"Binary switch command built (len={len(command)}): {command.hex()}")

    return command


# ----- SCAN INTERNAL HELPER FUNCTIONS -----

def _transact_switch(device: str, command: bytes, data_path: str | Path | None, log_path: Path | None = None, step: int = 0,) -> tuple[bytes, bool]:
    """Write one switch command and read response to sonar device.
    
    Args:
        device: Path to device as a string (from `init_serial()`).
        command: Raw switch command compiled from configuration settings as bytes (from `build_binary()`).
        data_path: Path to raw .dat data file.
        log_path: The path to the log file (from `create_log_file()`) as a string. If None, nothing is written.

    Returns:
        Raw sonar response as bytes.
        Transaction success or failure as boolean.

    Logs only on errors.
    """

    ok = True

    try:
        device.reset_input_buffer()
    except Exception as e:
        ok = False
        _append_log(log_path, f"Step {step}: failed to reset input buffer: {e}")

    # Write switch command to sonar
    try:
        sent_count = device.write(command)
        device.flush()
    except Exception as e:
        ok = False
        _append_log(log_path, f"Step {step}: failed to send command: {e}")
        return b"", False
    
    if sent_count != len(command):
        ok = False
        _append_log(log_path, f"Step {step}: sent {sent_count} bytes, expected {len(command)}")

    # Read sonar response
    try:
        read_data = device.read_until(b"\xfc")
    except Exception as e:
        ok = False
        _append_log(log_path, f"Step {step}: failed to read response: {e}")
        return b"", False

    # Ensure we received a response and that it ended with the correct terminator byte
    if not read_data or not read_data.endswith(b"\xfc"):
        ok = False
        _append_log(log_path, f"Step {step}: bad/unterminated response (len={len(read_data)})")

    # Write raw response to data file
    if data_path:
        try:
            with open(data_path, "ab") as file:
                file.write(read_data)
        except Exception as e:
            ok = False
            _append_log(log_path, f"Step {step}: failed to write raw data to {data_path}: {e}")

    return read_data, ok

def _parse_response(sonar_data: bytes, log_path: Path | None = None) -> tuple[dict, bool]:
    """Convert sonar response into dictionary with engineering units. 
    
    Args:
        sonar_data: The raw sonar response data in bytes.
        log_path: The path to the log file (from `create_log_file()`) as a string. If None, nothing is written.

    Returns: 
        Sonar response as dictionary in engineering units.
        Parse success or fail as boolean.

    Logs only on errors.
    """

    # Initialize response as an empty dictionary
    response: dict = {}

    # If the length of the raw sonar response is less than 12 bytes, write an error to log and flag a bad parse
    if len(sonar_data) <= 12:
        _append_log(log_path, f"Parse error: response too short (len={len(sonar_data)})")
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
        _append_log(log_path, f"Parse error: failed to parse response (len={len(sonar_data)}): {e}")
        return {}, False


# ----- SCAN PUBLIC FUNCTIONS -----

def sonar_scan(ops=dict, switch_cmd=dict, device=str, command=bytes, num_scan=int, log_path: Path | None = None):
    """Run a sonar scan and write raw data to .dat file (one per scan).
    
    Args:
        ops: Operational configuration parameters parsed into a dictionary (from `parse_config()`).
        switch_cmd: Switch command configuration parameters parsed into a dictionary (from `parse_config()`).
        device: Path to device as a string (from `init_serial()`).
        command: Raw switch command compiled from configuration settings as bytes (from `build_binary()`).
        num_scan: The number of the scan currently being executed as an integer.
        log_path: The path to the log file as a string (from `create_log_file()`). If None, nothing is written.
    """
    # Get datetime as human readable string    
    datetime = time.strftime("%Y-%m-%d_%H.%M.%S", time.gmtime())

    # Make .dat file to store raw data (one per scan)
    try:
        data_path = _make_file(Path("data") / f"{datetime}", f"scan_{num_scan}.dat")
    except Exception:
        _append_log(log_path, f"Failed to create data file at {data_path}")
        raise
    else:
        _append_log(log_path, f"Data file created at {data_path}")

    # Determine number of individual steps needed for a single sweep
    num_steps = int(float(switch_cmd["sector_width"]) / (float(switch_cmd["step_size"]) * 0.3))

    # Initialize variables for number of step successes / failures in a scan
    success = 0
    failure = 0

    # Write the beginning of scan to log
    _append_log(log_path, f"Starting Scan {num_scan}")

    # For each step in the number of 
    for i in range(num_steps):
        sonar_data, transaction_ok = _transact_switch(device=device, command=command, data_path=data_path, log_path=log_path, step=i,)

        response, parse_ok = _parse_response(sonar_data=sonar_data, log_path=log_path)
        ok = transaction_ok and parse_ok 

        if ok:
            success += 1
        else:
            failure += 1

    _append_log(
        log_path,
        f"Scan {num_scan} complete: steps={num_steps}, successful={success}, unsuccessful={failure}, data_file={data_path}",
    )