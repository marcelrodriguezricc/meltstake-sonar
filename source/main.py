# Import libraries
import utils

# Create log file and get path
log = utils.create_log_file()

# Initialize serial connection
ser = utils.init_serial(port="/dev/ttys010", log_path=log)

# Set global variables for deployment and switch command parameters based on configuration file
config = utils.parse_config(log_path=log)

# Build binary switch command from configuration parameters
binary_switch = utils.build_binary(params=config, log_path=log)
