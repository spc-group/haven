from unittest import mock
from tempfile import TemporaryDirectory
from pathlib import Path
from haven.export import build_queries, export_run


def test_build_quries_empty():
    qs = build_queries(exit_status=None)
    assert len(qs) == 0


def test_build_quries_with_filters():
    qs = build_queries(
        before="2025-10-05T08:00:00",
        after="2025-10-03T09:00:00",
        esaf="549301",
        proposal="22348",
        sample_name="NMC-833",
        plan_name="xafs_scan",
        sample_formula="NiMnCo",
        scan_name="pristine",
        edge="Ni-K",
        uid="a1b2c3d4-e5f6",
    )
    assert len(qs) == 11
    assert qs[0].key == "stop.exit_status"


async def test_export_run():
    run = mock.AsyncMock()
    run.metadata = {}
    with TemporaryDirectory() as tmp_dir:
        base_dir = Path(tmp_dir)
        await export_run(run, base_dir=base_dir, use_xdi=True)
    assert run.export.called
