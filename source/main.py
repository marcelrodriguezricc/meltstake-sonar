# Import libraries
import utils
from deploy import Deployment

# Parse arguments from CLI
# Example excution: "python3 source/main.py --config source/config.toml --deployment-number 0"
# Default config is source/config.toml, default deployment number = 0
args = utils.parse_args()

print(args)

# Initialize deployment
deploy = Deployment(
    num_deploy=args.num_deploy,
    config=args.config,
)

# Begin scan
deploy.start_scanning()

