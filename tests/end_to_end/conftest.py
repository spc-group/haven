import importlib
from pathlib import Path

import pytest

REPO_DIR = Path(__file__).parent.parent.parent
STARTUP_FILE = REPO_DIR / "src" / "haven" / "startup.py"


@pytest.fixture()
def startup():
    # Load the startup module
    spec = importlib.util.spec_from_file_location("startup", STARTUP_FILE)
    startup_ = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(startup_)
    try:
        yield startup_
    finally:
        startup_.writer.client.context.close()


# Override the fixture that sets testing iconfig files
@pytest.fixture(autouse=True)
def default_iconfig(monkeypatch):
    pass
