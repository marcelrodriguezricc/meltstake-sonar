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
    config: str | Path
    data_dir: Path
    data_path: Path
    init_time: str
    connection: dict
    switch_cmd: dict
    device: serial.Serial
    binary_switch: bytearray

    def __init__(self, config: str = "default_config.toml", data_dir: str | None = None):

        # Store inputs
        self.config = config
        self.data_dir = data_dir

        # Initialize data directory and log file
        bootstrap.init_data_dir(self.data_dir)
        bootstrap.create_log_file()

        # From configuration file - get connection, switch command, and operational parameters dictionaries
        self.connection, self.switch_cmd = bootstrap.parse_config(self.config)

        # Generate a run index csv file and configuration json for parsing of sonar data
        bootstrap.create_run_index()
        bootstrap.create_config_json(self.switch_cmd)

        # Initialize the serial connection
        self.device = bootstrap.init_serial(self.connection)

    def start_scan(self, stop_event: threading.Event | None = None) -> None:
        scan.scan(self, stop_event)