import serial
import threading
import logging
import threading
from pathlib import Path

from . import scan
from . import bootstrap
from . import utils

log = logging.getLogger(__name__)

class Handler:
    meltstake: str
    config: str | Path
    hardware: str
    log_path: Path
    connection: dict
    switch_cmd: dict
    device: serial.Serial
    binary_switch: bytearray
    start_dt: str

    def __init__(self, meltstake: str = "01", config: str = "default_config.toml", hardware: str = "2020"):

        # Store inputs
        self.meltstake = meltstake
        self.config = config
        self.hardware = hardware

        # Generate a log file and store path
        self.log_path, self.start_dt = bootstrap.create_log_file(self.meltstake, self.hardware)

        # From configuration file - get connection, switch command, and operational parameters dictionaries
        self.connection, self.switch_cmd = bootstrap.parse_config(self.config, self.log_path)

        # Initialize the serial connection
        self.device = bootstrap.init_serial(self.connection, log_path=self.log_path)

    def start_scan(self, stop_event: threading.Event | None = None) -> None:
        scan.scan(self.meltstake, self.hardware, self.start_dt, self.switch_cmd, self.device, self.log_path, stop_event)