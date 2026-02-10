import tomllib
import serial
import json
from serial.tools import list_ports
from datetime import datetime, timezone
from pathlib import Path

from . import utils
from . import scan

_DATA_PATH = None

# Default parameters, in case of configuration load failure
_DEFAULT_CONNECTION: dict[str, object] = {
    "device_name": "usbserial",
    "port": None,
}

_DEFAULT_SWITCH_CMD: dict[str, int] = {
    "num_sweeps": 2,    
    "range": 1,
    "freq": 165,
    "start_gain": 18,
    "logf": 0, 
    "absorption": 60,
    "train_angle": 60,
    "sector_width": 40,
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

def _set_default(dst: dict, key: str, default: object, why: str) -> None:
    """Sets input key to default value."""

    utils.append_log(f"Config '{key}' invalid ({why}); using default {default!r}")

    # Set input key to default
    dst[key] = default

def _clamp_int(dst: dict, key: str, default: int, lo: int, hi: int,) -> None:
    """Checks whether integer is in range of possible values; forces it to minimum if below, maximum if above, and default if input is not an integer."""

    # Get number from key
    raw = dst.get(key, None)

    # Set to integer
    n = _coerce_int(raw)

    # If None is returned, set to default
    if n is None:
        _set_default(dst, key, default, f"not an int: {raw!r}")
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

def _enum_int(dst: dict, key: str, default: int, allowed: set[int],) -> None:
    """"Checks whether input integer matches allowed values."""
    
    # Get key
    raw = dst.get(key, None)

    # If it's not an integer, change it to type integer, returns None if not possible
    n = _coerce_int(raw)

    # If the input cannot be coerced or allowed, set to default
    if n is None or n not in allowed:
        _set_default(dst, key, default, f"must be one of {sorted(allowed)}; got {raw!r}")
        return
    
    # Set input key
    dst[key] = n

def _load_config(config: str) -> dict:
    """Load configuration file from ROOT/configs directory.

    Falls back to default_config.toml if the requested config can't be loaded.
    """

    # Establish configuration path
    ROOT = Path(__file__).resolve().parents[2]
    configs_dir = ROOT / "configs"
    primary_path = configs_dir / Path(config)
    fallback_path = configs_dir / "default_config.toml"

    # Function to load configuration .toml file at given path as a dictionary
    def _try_load(path: Path) -> dict:
        with path.open("rb") as f:
            return tomllib.load(f)

    # Try requested config
    try:
        cfg = _try_load(primary_path)

    # If it fails, fallback to default_config.toml
    except (FileNotFoundError, tomllib.TOMLDecodeError, OSError) as e1:
        utils.append_log(f"Failed to load configuration file at {primary_path}: {e1}")

        # If primary already is the fallback, don't loop
        if primary_path.resolve() == fallback_path.resolve():
            raise

        utils.append_log(f"Falling back to default configuration at {fallback_path}")

        # Try default_config.toml
        try:
            cfg = _try_load(fallback_path)
        except (FileNotFoundError, tomllib.TOMLDecodeError, OSError) as e2:
            utils.append_log(f"Failed to load fallback configuration at {fallback_path}: {e2}")
            raise RuntimeError(
                f"Failed to load config {primary_path} and fallback {fallback_path}"
            ) from e2
        else:
            utils.append_log(f"Fallback configuration file loaded: {fallback_path}")
            return cfg
    else:
        utils.append_log(f"Configuration file loaded: {primary_path}")
        return cfg

def _auto_detect_port(device_name: str) -> str | None:
    """Automatic serial port detection."""

    # Check for name in names and descriptions for each port list of serial ports
    for p in list_ports.comports():
        if device_name in (p.device or "").lower() or device_name in (p.description or "").lower():
            return p.device
        
    return None


def init_data_dir(data_dir: str) -> None:
    """Initialize data directory for storage of files generated during runtime."""

    # Get datetime and format for file naming
    utc_dt = datetime.now(timezone.utc)
    dt_formatted = utc_dt.strftime("%Y-%m-%d_%H.%M.%S")
    data_path = f"{data_dir}/{dt_formatted}"
 
    # Set path to data directory as global variable in all modules
    global _DATA_PATH 
    _DATA_PATH = data_path
    utils.set_data_path(data_path)
    scan.set_data_path(data_path)

def create_log_file() -> None:
    """Create log file and write an init line."""

    # Create a log file at directory "logs"
    log_path = utils.make_file("sonar.log")

    utils.append_log(f"Melt Stake 881A Sonar deployment log initialized")
    utils.append_log(f"Path to log: {log_path}")

def create_run_index() -> None:
    """Create a run index of data filenames for parsing."""

    # Set path
    csv_path = f"{_DATA_PATH}/RunIndex.csv"

    # Initialize file
    try:
        with open(csv_path, "w") as outfile:
            outfile.write("Time Stamp,Type,File\n")
    except Exception as e:
        utils.append_log(f"Failed to create RunIndex.csv at {csv_path}: {e}")
    else:
        utils.append_log(f"Created RunIndex.csv at {csv_path}")

def create_config_json(switch_cmd: dict) -> None:
    """Write configuration to a json file for parsing."""

    # Set path
    json_path = Path(f"{_DATA_PATH}/configuration.json")

    # Create json file
    try:
        json_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        utils.append_log(f"Failed to create configuration.json at {json_path}: {e}")
    else:
        utils.append_log(f"Created configuration.json at {json_path}")

    # Append configuration dictionary to json
    try:
        with json_path.open("w", encoding="utf-8") as f:
            json.dump({"scan": switch_cmd}, f, indent=2, sort_keys=True)
            f.write("\n")
    except Exception as e:
        utils.append_log(f"Failed to write switch_cmd dictionary to configuration.json at {json_path}: {e}")
    else:
        utils.append_log(f"Wrote switch_cmd dictionary to configuration.json at {json_path}")
      

def parse_config(config: str) -> tuple[dict, dict]:
    """Parse configuration .toml file and return connection + switch parameters as dicts."""

    # Load configuration from .toml file
    cfg = _load_config(config)

    # Try to get connection and switch_cmd keys, if it fails, set to default
    try:
        connection = dict(cfg.get("connection", {}))
        switch_cmd = dict(cfg.get("switch_cmd", {}))
    except Exception as e:
        utils.append_log(f"Failed to parse configuration from config.toml: {e}, setting to default.")
        switch_cmd = _DEFAULT_SWITCH_CMD
        raise
    
    # Fill missing connection keys with defaults
    for k, v in _DEFAULT_CONNECTION.items():
        connection.setdefault(k, v)

    # Validate connection parameters
    connection["port"] = _norm_optional_str(connection.get("port"))
    connection["device_name"] = _norm_optional_str(connection.get("device_name"))

    # If both are missing, force a sane device_name default for auto-detect
    if connection["port"] is None and connection["device_name"] is None:
        _set_default(connection, "device_name", _DEFAULT_CONNECTION["device_name"], "both port and device_name missing/blank")

    # Fill missing switch command keys with defaults
    for k, v in _DEFAULT_SWITCH_CMD.items():
        switch_cmd.setdefault(k, v)

    # Validate switch command parameters
    _clamp_int(switch_cmd, "num_sweeps", _DEFAULT_SWITCH_CMD["num_sweeps"], 1, 10_000)
    _clamp_int(switch_cmd, "range", _DEFAULT_SWITCH_CMD["range"], 1, 200)
    _clamp_int(switch_cmd, "freq", _DEFAULT_SWITCH_CMD["freq"], 0, 200)
    _clamp_int(switch_cmd, "start_gain", _DEFAULT_SWITCH_CMD["start_gain"], 0, 40)
    _clamp_int(switch_cmd, "absorption", _DEFAULT_SWITCH_CMD["absorption"], 0, 255)
    _clamp_int(switch_cmd, "train_angle", _DEFAULT_SWITCH_CMD["train_angle"], 0, 120)
    _clamp_int(switch_cmd, "sector_width", _DEFAULT_SWITCH_CMD["sector_width"], 0, 120)
    _clamp_int(switch_cmd, "step_size", _DEFAULT_SWITCH_CMD["step_size"], 0, 8)
    _clamp_int(switch_cmd, "pulse_length", _DEFAULT_SWITCH_CMD["pulse_length"], 1, 100)
    _clamp_int(switch_cmd, "min_range", _DEFAULT_SWITCH_CMD["min_range"], 0, 250)
    _enum_int(switch_cmd, "logf", _DEFAULT_SWITCH_CMD["logf"], {0, 1, 2, 3})
    _enum_int(switch_cmd, "data_points", _DEFAULT_SWITCH_CMD["data_points"], {25, 50})

    utils.append_log(f"Configuration file parsed - {switch_cmd}")

    return connection, switch_cmd

def init_serial(connection: dict, baud: int = 115200, timeout: float = 1.0) -> serial.Serial:
    """Initialize and return a serial connection.

    Args:
        connection: Dictionary containing port and device name strings as set in configuration file (from `parse_config()`).
        timeout: Read/write timeout in seconds.

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
        utils.append_log("No serial port provided and auto-detection failed")
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
        utils.append_log(f"Failed to open serial port {port!r} at {baud} baud: {e}")
        raise
    else:
        utils.append_log(f"Serial port opened: {port!r} @ {baud} baud")

    # Reset read and write buffers
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    return ser