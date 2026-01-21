# Import libraries
from pathlib import Path
import tomllib
import time

# Load configuration file as a Python dictionary object
def load_config() -> dict: #
    cfg_path = Path(__file__).with_name("config.toml") # Get path to config.toml
    with cfg_path.open("rb") as f: # Open the file
        return tomllib.load(f) # Load the file


# Parse config.toml into discrete variables
def parse_config() -> None:

    cfg = load_config()
    
    global port
    global baud
    global max_range
    global freq
    global start_gain
    global logf
    global absorption
    global train_angle
    global sector_width
    global step_size
    global pulse_length
    global min_range
    global data_points

    port = cfg["connection"]["port"]
    baud = cfg["connection"]["baud"]
    max_range = cfg["sonar"]["max_range"]
    freq = cfg["sonar"]["freq"]
    start_gain = cfg["sonar"]["start_gain"]
    logf = cfg["sonar"]["logf"]
    absorption = cfg["sonar"]["absorption"]
    train_angle = cfg["sonar"]["train_angle"]
    sector_width = cfg["sonar"]["sector_width"]
    step_size = cfg["sonar"]["step_size"]
    pulse_length = cfg["sonar"]["pulse_length"]
    min_range = cfg["sonar"]["min_range"]
    data_points = cfg["sonar"]["min_range"]

def get_datetime():
    utcDateTime = time.gmtime()
    read_datetime = "{year:04d}-{month:02d}-{day:02d}_{hour:02d}.{minute:02d}.{second:02d}".format(year=utcDateTime.tm_year, month=utcDateTime.tm_mon, day=utcDateTime.tm_mday, hour=utcDateTime.tm_hour, minute=utcDateTime.tm_min, second=utcDateTime.tm_sec)
    return read_datetime

def build_binary(calibration: bool = False):
    command=bytearray(27)
    calibrate = int(bool(calibration))

    # Switch data header
    command[0] = bytearray.fromhex('fe')[0]
    command[1] = bytearray.fromhex('44')[0]

    command[2] = 16                          # Head ID
    command[3] = max_range                   # Range
    command[4] = 0                           # Reserved, must be 0
    command[5] = 0                           # Rev / hold
    command[6] = bytearray.fromhex('43')[0]  # Master / Slave (always slave)
    command[7] = 0                           # Reserved, must be 0

    command[8] = start_gain                        # Start Gain
    command[9] = logf                        # Logf (0=10dB 1=20dB 2=30dB 3=40dB)
    command[10] = absorption                 # Absorption dB per m * 100 - Do not use a value of 253 (\xfd)
    command[11] = train_angle                # (Train angle in degrees + 180) / 3 - 60 is 0 degrees
    command[12] = sector_width               # Sector width in 3-degree steps - 60 is 180 degrees
    command[13] = step_size                  # Step size (0 to 8 in 0.3-degree steps) - 4 is 1.2 degrees/step
    command[14] = pulse_length               # Pulse length 1-100 -> 10 to 1000 usec in 10-usec increments - usec / 10
    command[15] = 0                          # Profile Minimum Range: 0-250 -> 0 to 25 meters in 0.1-meter increments

    command[16] = 0                          # Reserved, must be 0
    command[17] = 0                          # Reserved, must be 0
    command[18] = 0                          # Reserved, must be 0
    command[19] = data_points                # 25 - 250 data points returned, header 'IMX'   50 - 500 data points returned, header 'IGX'
    command[20] = 8                          # 4, 8, 16: resolution.  8 is 8-bit data, one sample per byte.
    command[21] = bytearray.fromhex('06')[0] # up baud: \x0b 9600, \x03 14400, \x0c 19200, \x04 28800, \x02 38400, \x05 57600, \x06 115200
    command[22] = 0                          # 0 - off, 1 = on
    command[23] = calibrate                  # calibrate, 0 = off, 1 = on

    command[24] = 1                          # Switch delay 0-255 in 2-msec increments - Do not use value of 253 (\fd)
    command[25] = freq                       # 0-200 in (kHz - 675)/5 + 100 - 175kHz-1175kHz in 5kHz increments

    # Termination byte
    command[26] = bytearray.fromhex('fd')[0]

    return command


