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

    default_config = str(Path(__file__).with_name("config.toml"))

    # Path to TOML configuration file
    p.add_argument(
        "-c",
        "--config",
        default=default_config,
        help="Path to TOML config (default: config.toml)",
    )

    # Deployment number
    p.add_argument(
        "-n",
        "--num_deploy",
        type=int,
        default=0,
        help="Deployment number (default: 0)",
    )

    return p.parse_args()