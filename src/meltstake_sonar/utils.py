from pathlib import Path
import time
import argparse

def _utc_time_part() -> str:
    """Return the current UTC time as HH:MM:SS."""

    # Get UTC time in human-readable format (hours.minutes.seconds)
    my_time = time.strftime("%H:%M:%S", time.gmtime())

    return my_time

def append_log(log_path: Path, line: str) -> None:
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

def make_file(dir: str | Path, filename: str) -> Path:
    """Create a path under `dir`, creating the directory if needed.

    Args:
        dir: Directory where file will be saved, creates one if none exists
        filename: Name of file with suffix
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

    default_config = "config.toml"

    # Path to TOML configuration file
    p.add_argument(
        "-c",
        "--config",
        default=default_config,
        help="Path to TOML config (default: config.toml)",
    )

    # Deployment number
    p.add_argument(
        "-d",
        "--deployment",
        type = str,
        default = "01",
        help = "Deployment number (default: 01)",
    )

    return p.parse_args()

def build_binary(switch_cmd: dict, calibration: bool = False, log_path: str | None = None, reverse: bool = False, no_step: bool = False, tag: str | None = None):
    """Build the 27-byte 881A sonar switch command from switch_cmd dictionary.

    This constructs a fixed-length `bytearray(27)` using values from `switch_cmd`
    and optionally enables calibration.

    Args:
        switch_cmd: Dictionary of switch parameters (from `parse_config()`).
        calibration: If True, sets the calibration flag byte in the command.
        log_path: Path to the log file. If None, nothing is written.
        reverse: Whether switch command will move sonar head cw/ccw.

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

    # Set bit 6 of byte 5 to 1 if reverse, 0 if normal operation
    rev = 0x40 if reverse else 0x00

    step_size = 0 if no_step else switch_cmd["step_size"]

    # Compile byte command payload based on switch command configuration settings
    try:
        command[0] = 0xFE                        # Switch data header
        command[1] = 0x44                        # Switch data header
        command[2] = 16                          # Head ID
        command[3] = switch_cmd["max_range"]     # Range
        command[4] = 0                           # Reserved, must be 0
        command[5] = rev                           # Rev / hold
        command[6] = 0x43                        # Master / Slave (always slave)
        command[7] = 0                           # Reserved, must be 0
        command[8]  = switch_cmd["start_gain"]   # Start Gain
        command[9]  = switch_cmd["logf"]         # Logf
        command[10] = switch_cmd["absorption"]   # Absorption
        command[11] = switch_cmd["train_angle"]  # Train angle
        command[12] = switch_cmd["sector_width"] # Sector width
        command[13] = step_size                       # Step size
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
        append_log(log_path, f"Failed to build binary command from switch_cmd: {e}")
        raise
    else:
        append_log(log_path, f"{tag} binary switch command built (len={len(command)}): {command.hex()}")

    return command