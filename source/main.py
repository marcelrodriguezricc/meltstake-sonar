# Import libraries
import utils

# Create log file and get path
log_path = utils.create_log_file()

# Set global variables for deployment and switch command parameters based on configuration file
connection, ops, switch_cmd = utils.parse_config(log_path=log_path)

print(connection)

# Initialize serial connection
device = utils.init_serial(connection=connection, log_path=log_path)

# Build binary switch command from configuration parameters
binary_switch = utils.build_binary(switch_cmd=switch_cmd, log_path=log_path)

# Send swtich command and read response
utils.sonar_scan(ops=ops, switch_cmd=switch_cmd, device=device, command=binary_switch, num_scan=0, log_path=log_path)