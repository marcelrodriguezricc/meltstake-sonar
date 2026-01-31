import serial
from pathlib import Path

from . import scan
from . import bootstrap

class Deployment:
    deployment: int
    config: str | Path
    log_path: Path
    connection: dict
    ops: dict
    switch_cmd: dict
    device: serial.Serial
    binary_switch: bytearray

    def __init__(self, deployment: int = 0, config: str = "config.toml"):

        # Store inputs
        self.deployment = deployment
        self.config = config

        # Generate a log file and store path
        self.log_path = bootstrap.create_log_file(self.deployment)

        # From configuration file - get connection, switch command, and operational parameters dictionaries
        self.connection, self.ops, self.switch_cmd = bootstrap.parse_config(self.config, self.log_path)

        # Initialize the serial connection
        self.device = bootstrap.init_serial(self.connection, log_path=self.log_path)

    def start_scanning(self):
        scan.scan_sector(self.deployment, self.ops, self.switch_cmd, self.device, 0, self.log_path)