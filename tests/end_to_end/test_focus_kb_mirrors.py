import shutil
from pathlib import Path

import pytest

from haven.plans import focus_kb_mirrors

OPTICAL_SYSTEM = "25-ID-C"


@pytest.fixture()
def config_path(tmp_path):
    src = Path("~/src/AI-Beamline-25ID/TEST/25-ID-C/").expanduser()
    # src = Path(load_config()['optics_alignemnt']['config_directory'])
    new_path = shutil.copytree(src, tmp_path / OPTICAL_SYSTEM, dirs_exist_ok=True)
    return new_path


@pytest.mark.beamline()
def test_runs_with_digital_twin(config_path):
    msgs = list(
        focus_kb_mirrors(base_directory=config_path.parent, optical_system_id="25-ID-C")
    )
