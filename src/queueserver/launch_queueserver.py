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
    default_config_file = str(bluesky_dir / "iconfig.toml")
    config_files = os.environ.setdefault(
        "HAVEN_CONFIG_FILES", default_config_file
    ).split(",")
    # Derive internal haven variables

    config = load_config(file_paths=config_files)
    control_port = config["queueserver"]["control_port"]
    info_port = config["queueserver"]["info_port"]
    redis_addr = config["queueserver"]["redis_addr"]
    # Launch the queueserver
    args = [
        "start-re-manager",
        "--startup-script",
        str(this_dir / "queueserver_startup.py"),
        "--existing-plans-devices",
        str(bluesky_dir / "queueserver_existing_plans_and_devices.yaml"),
        "--user-group-permissions",
        str(this_dir / "queueserver_user_group_permissions.yaml"),
        "--zmq-control-addr",
        f"tcp://*:{control_port}",
        "--zmq-info-addr",
        f"tcp://*:{info_port}",
        "--redis-addr",
        redis_addr,
        "--keep-re",
        "--update-existing-plans-devices",
        "ENVIRONMENT_OPEN",
        "--use-ipython-kernel=ON",
    ]
    log.info(f"Starting queueserver with command: {' '.join(args)}")
    subprocess.run(args)
