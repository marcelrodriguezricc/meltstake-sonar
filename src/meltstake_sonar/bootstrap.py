import tomllib
import serial
from serial.tools import list_ports
from datetime import datetime, timezone
from pathlib import Path
from . import utils

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
    utils.append_log(log_path, f"Melt Stake 881A Sonar deployment log initialized - {utc_date_str}")

    return log_path

def parse_config(config: str, log_path: Path | None) -> tuple[dict,dict,dict]:
    """Parse config.toml and return the sonar switch parameters as a dict.

    Args:
        config: Filename of configuration file to be loaded in /configs directory as string.
        log_path: Path to the log file. If None, nothing is written.

    Returns:
        1) dictionary of connection parameters, 2) dictionary of operational parameters,
        3) dictionary of switch parameters used to build the binary switch command.

    Raises:
        KeyError: If required config keys are missing (e.g., [switch] or fields within it).
        TypeError: If the loaded config structure is not subscriptable as expected.
        FileNotFoundError: If config.toml does not exist.
        tomllib.TOMLDecodeError: If config.toml is not valid TOML.
        OSError: If the file cannot be read due to an OS-level error.
    """

    # Load the configuration file as a dictionary
    cfg = _load_config(config, log_path)
    
    # Separate system and switch settings
    try:
        connection = cfg["connection"]
        ops = cfg["ops"]
        switch_cmd = cfg["switch_cmd"]
    except (KeyError, TypeError) as e:
        utils.append_log(log_path, f"Failed to parse configuration from config.toml: {e}")
        raise
    else:
        utils.append_log(log_path, f"Configuration loaded from config.toml")

    # Handle unspecified arguments in configuration file by setting to None
    port = connection.get("port")
    if port == "" or port is None:
        connection["port"] = None
    device_name = connection.get("device_name")
    if device_name == "" or device_name is None:
        connection["device_name"] = None

    return connection, ops, switch_cmd

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
    command = bytearray(27)

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
        utils.append_log(log_path, f"Failed to build binary command from switch_cmd: {e}")
        raise
    else:
        utils.append_log(log_path, f"Binary switch command built (len={len(command)}): {command.hex()}")

    return command