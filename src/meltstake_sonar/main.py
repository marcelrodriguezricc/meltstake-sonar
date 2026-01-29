from . import utils
from meltstake_sonar.deploy import Deployment

def main() -> None:

    # Get arguments from CLI execution
    args = utils.parse_args()

    # Create deployment object - on initialization generates log file, loads configuration, initializes the serial connection, and builds the binary switch command
    deploy = Deployment(
        deployment=args.deployment,
        config=args.config,
    )

    # Initiates sonar scan
    deploy.start_scanning()

if __name__ == "__main__":
    main()