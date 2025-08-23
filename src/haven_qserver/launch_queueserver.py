import sys
import logging
import os
import subprocess
from pathlib import Path

from haven import load_config

log = logging.getLogger(__name__)


def launch_queueserver():
    # Derive environmental variables
    this_dir = Path(__file__).parent
    bluesky_dir = Path(os.environ["BLUESKY_DIR"])

    # Derive internal haven variables
    config = load_config()
    redis_addr = config.get("queueserver", {}).get("redis_addr", "")
    # Launch the queueserver
    args = [
        "start-re-manager",
        "--config",
        str(this_dir / "qs_config.yml"),
        "--existing-plans-devices",
        str(bluesky_dir / "queueserver_existing_plans_and_devices.yaml"),
        "--user-group-permissions",
        str(this_dir / "queueserver_user_group_permissions.yaml"),
        "--redis-addr",
        redis_addr,
    ]
    log.info(f"Starting queueserver with command: {' '.join(args)}")
    subprocess.run(args)


if __name__ == "__main__":
    sys.exit(launch_queueserver())
