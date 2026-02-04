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
    num_deploy: int
    config: str | Path
    log_path: Path
    connection: dict
    switch_cmd: dict
    device: serial.Serial
    binary_switch: bytearray

    def __init__(self, num_deploy: int = 0, config: str = "default_config.toml"):

        # Store inputs
        self.num_deploy = num_deploy
        self.config = config

        # Generate a log file and store path
        self.log_path = bootstrap.create_log_file(self.num_deploy)

        # From configuration file - get connection, switch command, and operational parameters dictionaries
        self.connection, self.switch_cmd = bootstrap.parse_config(self.config, self.log_path)

        # Initialize the serial connection
        self.device = bootstrap.init_serial(self.connection, log_path=self.log_path)

    def start_scan(self, stop_event: threading.Event | None = None) -> None:
        scan.scan(self.num_deploy, self.switch_cmd, self.device, self.log_path, stop_event)