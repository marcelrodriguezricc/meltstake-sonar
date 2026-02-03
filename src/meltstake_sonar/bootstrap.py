import tomllib
import serial
from serial.tools import list_ports
from datetime import datetime, timezone
from pathlib import Path
from . import utils

_DEFAULT_CONNECTION: dict[str, object] = {
    "device_name": "usbserial",
    "port": None,
}

_DEFAULT_SWITCH_CMD: dict[str, int] = {
    "num_sweeps": 2,    
    "max_range": 1,
    "freq": 165,
    "start_gain": 18,
    "logf": 0, 
    "absorption": 60,
    "train_angle": 60,
    "sector_width": 10,
    "step_size": 1,
    "pulse_length": 2,
    "min_range": 0,
    "data_points": 50,
}

def _norm_optional_str(val: object) -> str | None:
    """Checks for an input; if it's a string, strips whitespace from string if present."""

    # If no input is given, return None
    if val is None:
        return None
    
    # Strip whitespace, return none if all whitespace
    if isinstance(val, str):
        s = val.strip()
        return None if s == "" else s
    
    return str(val).strip() or None

def _coerce_int(val: object) -> int | None:
    """If input is not an integer, trys to set it to be an integer, if not returns None."""

    # If entry is a boolean, return none
    if isinstance(val, bool):
        return None
    
    # If entry is an integer, return normally
    if isinstance(val, int):
        return val
    
    # If entry is a float, convert to integer
    if isinstance(val, float) and val.is_integer():
        return int(val)
    
    # If entry is a string, convert to integer, if blank return none
    if isinstance(val, str):
        s = val.strip()
        if s == "":
            return None
        try:
            return int(s, 10)
        except ValueError:
            return None
        
    return None

def _set_default(log_path: Path | None, dst: dict, key: str, default: object, why: str) -> None:
    """Sets input key to default value."""
    utils.append_log(log_path, f"Config '{key}' invalid ({why}); using default {default!r}")

    # Set input key to default
    dst[key] = default

def _clamp_int(log_path: Path | None, dst: dict, key: str, default: int, lo: int, hi: int,) -> None:
    """Checks whether integer is in range of possible values; forces it to minimum if below, maximum if above, and default if input is not an integer."""

    # Get number from key
    raw = dst.get(key, None)

    # Set to integer
    n = _coerce_int(raw)

    # If None is returned, set to default
    if n is None:
        _set_default(log_path, dst, key, default, f"not an int: {raw!r}")
        return
    
    # If integer is below minimum, set to minimum
    if n < lo:
        n = lo
        return
    
    # If integer is above maximum, set to maximum
    if n > hi:
        n = hi
        return
    
    # Set input key
    dst[key] = n

def _enum_int(log_path: Path | None, dst: dict, key: str, default: int, allowed: set[int],) -> None:
    """"Checks whether input integer matches allowed values."""
    
    # Get key
    raw = dst.get(key, None)

    # If it's not an integer, change it to type integer, returns None if not possible
    n = _coerce_int(raw)

    # If the input cannot be coerced or allowed, set to default
    if n is None or n not in allowed:
        _set_default(log_path, dst, key, default, f"must be one of {sorted(allowed)}; got {raw!r}")
        return
    
    # Set input key
    dst[key] = n

def _load_config(config: str, log_path: Path | None) -> dict:
    """Load configuration file from ROOT/configs directory"""

    # Set path to configuration file
    filename = Path(config) 
    ROOT = Path(__file__).resolve().parents[2]
    cfg_path = ROOT / "configs" / filename

    # Load the configuration as a Python dictionary
    try:
        with cfg_path.open("rb") as f:
            cfg = tomllib.load(f)
    except (FileNotFoundError, tomllib.TOMLDecodeError, OSError) as e:
        utils.append_log(log_path, f"Failed to load configuration file at {cfg_path}: {e}")
        raise
    else:
        utils.append_log(log_path, f"Configuration file loaded: {cfg_path}")
    return cfg

def _auto_detect_port(device_name: str) -> str | None:
    """Automatic serial port detection."""

    # Check for name in names and descriptions for each port list of serial ports
    for p in list_ports.comports():
        if device_name in (p.device or "").lower() or device_name in (p.description or "").lower():
            return p.device
        
    return None

def create_log_file(deployment: int) -> Path:
    """Create ./logs/deployment_XX.log and write an init line."""

    # Create a log file at directory "logs"
    log_path = utils.make_file("logs", f"deployment_{deployment}.log")
    utc_date = datetime.now(timezone.utc).date() 
    utc_date_str = utc_date.isoformat() 
    utils.append_log(log_path, f"Melt Stake 881A Sonar deployment log initialized - Deployment {deployment} - {utc_date_str}")

    return log_path

def parse_config(config: str, log_path: Path | None) -> tuple[dict, dict]:
    """Parse configuration .toml file and return connection + switch parameters as dicts."""
    cfg = _load_config(config, log_path)

    try:
        connection = dict(cfg.get("connection", {}))
        switch_cmd = dict(cfg.get("switch_cmd", {}))
    except Exception as e:
        utils.append_log(log_path, f"Failed to parse configuration from config.toml: {e}, setting to default.")
        switch_cmd = _DEFAULT_SWITCH_CMD
        raise

    # ---- CONNECTION defaults + normalization ----
    # Defaults first
    for k, v in _DEFAULT_CONNECTION.items():
        connection.setdefault(k, v)

    connection["port"] = _norm_optional_str(connection.get("port"))
    connection["device_name"] = _norm_optional_str(connection.get("device_name"))

    # If both are missing, force a sane device_name default for auto-detect
    if connection["port"] is None and connection["device_name"] is None:
        _set_default(log_path, connection, "device_name", _DEFAULT_CONNECTION["device_name"], "both port and device_name missing/blank")

    # Set everything to default, 
    for k, v in _DEFAULT_SWITCH_CMD.items():
        switch_cmd.setdefault(k, v)


    _clamp_int(log_path, switch_cmd, "num_sweeps", _DEFAULT_SWITCH_CMD["num_sweeps"], 1, 10_000)
    _clamp_int(log_path, switch_cmd, "max_range", _DEFAULT_SWITCH_CMD["max_range"], 1, 200)
    _clamp_int(log_path, switch_cmd, "freq", _DEFAULT_SWITCH_CMD["freq"], 0, 200)
    _clamp_int(log_path, switch_cmd, "start_gain", _DEFAULT_SWITCH_CMD["start_gain"], 0, 40)
    _clamp_int(log_path, switch_cmd, "absorption", _DEFAULT_SWITCH_CMD["absorption"], 0, 255)
    _clamp_int(log_path, switch_cmd, "train_angle", _DEFAULT_SWITCH_CMD["train_angle"], 0, 120)
    _clamp_int(log_path, switch_cmd, "sector_width", _DEFAULT_SWITCH_CMD["sector_width"], 0, 120)
    _clamp_int(log_path, switch_cmd, "step_size", _DEFAULT_SWITCH_CMD["step_size"], 0, 8)
    _clamp_int(log_path, switch_cmd, "pulse_length", _DEFAULT_SWITCH_CMD["pulse_length"], 1, 100)
    _clamp_int(log_path, switch_cmd, "min_range", _DEFAULT_SWITCH_CMD["min_range"], 0, 250)
    _enum_int(log_path, switch_cmd, "logf", _DEFAULT_SWITCH_CMD["logf"], {0, 1, 2, 3})
    _enum_int(log_path, switch_cmd, "data_points", _DEFAULT_SWITCH_CMD["data_points"], {25, 50})


    


    return connection, switch_cmd

def init_serial(connection: dict, baud: int = 115200, timeout: float = 1.0, log_path: str | None = None) -> serial.Serial:
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
    
    # Get variables from connection configuration
    port = connection["port"]
    device_name = connection["device_name"]

    # If no port is specified, auto-detect which port the device is on
    if port is None:
        port = _auto_detect_port(device_name)

    # If no port, raise an error
    if port is None or str(port).strip() == "":
        utils.append_log(log_path, "No serial port provided and auto-detection failed")
        raise serial.SerialException("No serial port provided and auto-detection failed")
    
    # Try to connect to device
    try:
        ser = serial.Serial(
            port = port,
            baudrate = baud,
            bytesize = serial.EIGHTBITS,
            parity = serial.PARITY_NONE,
            stopbits = serial.STOPBITS_ONE,
            timeout = timeout,
            write_timeout = timeout,
        )
    except (serial.SerialException, OSError) as e:
        utils.append_log(log_path, f"Failed to open serial port {port!r} at {baud} baud: {e}")
        raise
    else:
        utils.append_log(log_path, f"Serial port opened: {port!r} @ {baud} baud")

    # Reset read and write buffers
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    return ser