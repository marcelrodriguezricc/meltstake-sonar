# Import libraries
import os
from pathlib import Path
import serial
from serial.tools import list_ports
import tomllib
import time

# ----- INTERNAL HELPERS -----

def _utc_time_part() -> str:
    """Return the current UTC time as HH:MM:SS."""

    return time.strftime("%H:%M:%S", time.gmtime())

def _append_log(log_path: Path, line: str) -> None:
    """Append a line to the log file with a UTC time prefix.

    Args:
        log_path: Path to the log file.
        line: Message to append (a trailing newline is added automatically).
    """

    if log_path is None:
        return
    
    prefix = _utc_time_part()

    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"{prefix}: {line.rstrip()}\n")

def _make_file(dir: str | Path, filename: str) -> Path:
    """Create a path under `dir`, creating the directory if needed.

    Args:
        dir: Directory where file will be saved, creates one if none exists
        filenname: Name of file with suffix
    """

    out_dir = Path(dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename

    return out_path

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

    cfg_path = Path(__file__).with_name("config.toml")

    try:
        with cfg_path.open("rb") as f:
            cfg = tomllib.load(f)
    except (FileNotFoundError, tomllib.TOMLDecodeError, OSError) as e:
        _append_log(log_path, f"Failed to load configuration file at {cfg_path}: {e}")
        raise
    else:
        _append_log(log_path, f"Configuration file loaded: {cfg_path}")

    return cfg

# ----- PUBLIC FUNCTIONS -----

def create_log_file() -> Path:
    """Create ./logs/<YYYY-MM-DD_HH-MM-SS>.log (UTC) and write an init line."""

    datetime = time.strftime("%Y-%m-%d_%H.%M.%S", time.gmtime())
    log_path = _make_file("logs", f"{datetime}.log")
    log_path.touch(exist_ok=True)
    _append_log(log_path, "Melt Stake 881A Sonar deployment log initialized")

    return log_path

def parse_config(log_path: Path | None) -> dict:
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

    cfg = _load_config(log_path)
    
    try:
        sw = cfg["switch"]
        params = {
            "max_range": sw["max_range"],
            "freq": sw["freq"],
            "start_gain": sw["start_gain"],
            "logf": sw["logf"],
            "absorption": sw["absorption"],
            "train_angle": sw["train_angle"],
            "sector_width": sw["sector_width"],
            "step_size": sw["step_size"],
            "pulse_length": sw["pulse_length"],
            "min_range": sw["min_range"],
            "data_points": sw.get("data_points", sw["min_range"]),
        }
    except (KeyError, TypeError) as e:
        _append_log(log_path, f"Failed to parse [switch] parameters from config.toml: {e}")
        raise
    else:
        _append_log(log_path, f"Switch parameters loaded: {params}")

    return params

# TODO: Adjust to match Sonar
def auto_detect_port() -> str | None:
    """Automatic serial port detection."""

    for p in list_ports.comports():
        if "usb" in (p.device or "").lower() or "usb" in (p.description or "").lower():
            return p.device
        
    return None

def init_serial(port: str | None = None, baud: int = 115200, timeout: float = 10.0, log_path: str | None = None) -> serial.Serial:
    """Initialize and return a serial connection.

    Args:
        port: Serial device path (e.g. /dev/cu.usbmodem*). If None, auto-detect is used.
        baud: Baud rate.
        timeout: Read/write timeout in seconds.
        log_path: Path to log file; if None, nothing is written.

    Returns:
        An opened `serial.Serial` instance.

    Raises:
        serial.SerialException: If no port is available or the port cannot be opened.
        OSError: If the OS refuses access to the device (permissions/in-use).
    """

    if port is None:
        port = auto_detect_port()

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

def build_binary(params: dict, calibration: bool = False, log_path: str | None = None):
    """Build the 27-byte 881A sonar switch command from params dictionary.

    This constructs a fixed-length `bytearray(27)` using values from `params`
    and optionally enables calibration.

    Args:
        params: Dictionary of switch parameters (typically from `parse_config()`).
            Required keys:
                - max_range, freq, start_gain, logf, absorption,
                  train_angle, sector_width, step_size, pulse_length,
                  data_points
        calibration: If True, sets the calibration flag byte in the command.
        log_path: Path to the log file. If None, nothing is written.

    Returns:
        A 27-byte command payload as a `bytearray`.

    Raises:
        KeyError: If `params` is missing a required key.
        TypeError: If `params` is not subscriptable or contains incompatible value types.
    """
    
    command=bytearray(27)
    calibrate = int(bool(calibration))


    try:
        # Switch data header
        command[0] = 0xFE
        command[1] = 0x44

        command[2] = 16                          # Head ID
        command[3] = params["max_range"]         # Range
        command[4] = 0                           # Reserved, must be 0
        command[5] = 0                           # Rev / hold
        command[6] = 0x43                        # Master / Slave (always slave)
        command[7] = 0                           # Reserved, must be 0

        command[8]  = params["start_gain"]       # Start Gain
        command[9]  = params["logf"]             # Logf
        command[10] = params["absorption"]       # Absorption
        command[11] = params["train_angle"]      # Train angle
        command[12] = params["sector_width"]     # Sector width
        command[13] = params["step_size"]        # Step size
        command[14] = params["pulse_length"]     # Pulse length
        command[15] = 0                          # Profile Minimum Range (reserved/unused here)

        command[16] = 0                          # Reserved, must be 0
        command[17] = 0                          # Reserved, must be 0
        command[18] = 0                          # Reserved, must be 0
        command[19] = params["data_points"]      # Data points
        command[20] = 8                          # Resolution (8-bit)
        command[21] = 0x06                       # 115200
        command[22] = 0                          # 0 - off, 1 = on
        command[23] = calibrate                  # calibrate, 0 = off, 1 = on

        command[24] = 1                          # Switch delay
        command[25] = params["freq"]             # Frequency

        # Termination byte
        command[26] = 0xFD

    except (KeyError, TypeError) as e:
        _append_log(log_path, f"Failed to build binary command from params: {e}")
        raise
    else:
        _append_log(log_path, f"Binary switch command built (len={len(command)}): {command.hex()}")

    return command


