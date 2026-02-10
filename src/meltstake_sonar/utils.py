from pathlib import Path
import time
import argparse
import logging


log = logging.getLogger(__name__)
_DATA_PATH = None

def _utc_time_part() -> str:
    """Return the current UTC time as HH:MM:SS."""

    # Get UTC time in human-readable format (hours.minutes.seconds)
    my_time = time.strftime("%H:%M:%S", time.gmtime())

    return my_time

def set_data_path(data_path):
    """Set global data path variable for "utils" module."""
    global _DATA_PATH
    _DATA_PATH = data_path

def append_log(line: str) -> None:
    """Append a line to the log file with a UTC time prefix.

    Args:
        line: Message to append (a trailing newline is added automatically).
    """

    # Get path to data directory from global variable (set during initialization)
    data_path = _DATA_PATH
    
    # UTC time to prepend each log entry
    prefix = _utc_time_part()

    # If debug mode enabled, print all logged lines to console
    log.debug(line)

    log_path = Path(f"{data_path}/sonar.log")

    # Open file and append line
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"{prefix}: {line.rstrip()}\n")

def make_file(filename: str) -> Path:
    """Create a path under `dir`, creating the directory if needed.

    Args:
        filename: Name of file with suffix
    """

    # Prepend user home directory
    out_dir = Path(_DATA_PATH).expanduser()

    # Make directory if it doesn't already exist
    out_dir.mkdir(parents=True, exist_ok=True)

    # Set file path with directory/filename
    out_path = out_dir / filename

    # Create file
    out_path.touch(exist_ok=True)

    return out_path

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for running a Melt Stake 881A sonar deployment.

    This defines the CLI interface for selecting a TOML configuration file and a
    deployment identifier, then returns the parsed values as an argparse Namespace.

    Returns:
        argparse.Namespace: Parsed CLI arguments with attributes:
            - config (str): Path to the TOML configuration file.
            - deployment_number (int): Deployment number identifier.
    """

    p = argparse.ArgumentParser(description="Melt Stake 881A Sonar deployment runner")

    # Default configuration file
    default_config = "default_config.toml"

    # Get repository root
    ROOT = Path(__file__).resolve().parents[2]
    default_data_dir = ROOT / "data"

    # Debugging mode, prints log entries to console
    p.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    # Path to TOML configuration file
    p.add_argument(
        "-c",
        "--config",
        default=default_config,
        help="Path to TOML config (default: default_config.toml)",
    )

        # Path to TOML configuration file
    p.add_argument(
        "-d",
        "--data",
        "--data-path",
        "--data-dir",
        default=default_data_dir,
        help="Path where data, logs, and other files created at runtime will be stored (default: ROOT/data)",
    )

    return p.parse_args()

def build_binary(switch_cmd: dict, calibration: bool = False, no_step: bool = False, tag = str):
    """Build the 27-byte 881A sonar switch command from switch_cmd dictionary.

    This constructs a fixed-length `bytearray(27)` using values from `switch_cmd`
    and optionally enables calibration.

    Args:
        switch_cmd: Dictionary of switch parameters (from `parse_config()`).
        calibration: If True, sets the calibration flag byte in the command.

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

    # Set step size to 0 no_step argument is set to true
    step_size = 0 if no_step else switch_cmd["step_size"]

    # Compile byte command payload based on switch command configuration settings
    try:
        command[0] = 0xFE                        # Switch data header
        command[1] = 0x44                        # Switch data header
        command[2] = 16                          # Head ID
        command[3] = switch_cmd["range"]         # Range
        command[4] = 0                           # Reserved, must be 0
        command[5] = 0                           # Rev / hold
        command[6] = 0x43                        # Master / Slave (always slave)
        command[7] = 0                           # Reserved, must be 0
        command[8]  = switch_cmd["start_gain"]   # Start Gain
        command[9]  = switch_cmd["logf"]         # Logf
        command[10] = switch_cmd["absorption"]   # Absorption
        command[11] = switch_cmd["train_angle"]  # Train angle
        command[12] = switch_cmd["sector_width"] # Sector width
        command[13] = step_size                  # Step size
        command[14] = switch_cmd["pulse_length"] # Pulse length
        command[15] = switch_cmd["min_range"]    # Profile Minimum Range (reserved/unused here)
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
        append_log(f"Failed to build binary command {tag} from switch_cmd: {e}")
        raise
    else:
        append_log(f"Binary switch command {tag} built (len={len(command)}): {command.hex()}")

    return command