import serial
from pathlib import Path

from . import scan
from . import bootstrap

class Deployment:
    num_deploy: int
    config: str | Path
    log_path: Path
    connection: dict
    ops: dict
    switch_cmd: dict
    device: serial.Serial
    binary_switch: bytearray

    def __init__(self, num_deploy: int = 0, config: str = "config.toml"):

        # Store inputs
        self.num_deploy = num_deploy
        self.config = config

        # Generate a log file and store path
        self.log_path = bootstrap.create_log_file(self.num_deploy)

        # From configuration file - get connection, switch command, and operational parameters dictionaries
        self.connection, self.ops, self.switch_cmd = bootstrap.parse_config(self.config, self.log_path)

        # Initialize the serial connection
        self.device = bootstrap.init_serial(self.connection, log_path=self.log_path)

        # Build binary
        self.binary_switch = bootstrap.build_binary(self.switch_cmd, log_path=self.log_path)

    def start_scanning(self):
        scan.scan_sector(self.num_deploy, self.ops, self.switch_cmd, self.device, self.binary_switch, 0, self.log_path)