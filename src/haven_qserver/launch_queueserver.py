import logging
import os
import subprocess
import sys
from pathlib import Path

from haven import load_config

log = logging.getLogger(__name__)


def launch_queueserver():
    # Derive environmental variables
    this_dir = Path(__file__).parent
    bluesky_dir = Path(os.environ["BLUESKY_DIR"])

    # Derive internal haven variables
    config = load_config()
    qs_config = config.get("queueserver", {})
    redis_addr = qs_config.get("redis_addr", "")
    redis_prefix = qs_config.get("redis_prefix", "qs_default")
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
        "--redis-name-prefix",
        redis_prefix,
    ]
    log.info(f"Starting queueserver with command: {' '.join(args)}")
    subprocess.run(args)


if __name__ == "__main__":
    sys.exit(launch_queueserver())
