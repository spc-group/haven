import io
from unittest import mock
from tempfile import TemporaryDirectory, NamedTemporaryFile
from pathlib import Path

import pytest
import numpy as np
import h5py

from haven.export import build_queries, export_run, harden_link

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


@pytest.fixture()
def temp_h5_file():
    fd = NamedTemporaryFile(delete=False, suffix=".h5")
    try:
        yield fd
    except:
        fd.delete()
        raise


async def test_harden_link(temp_h5_file):
    src_file = NamedTemporaryFile(delete_on_close=False, suffix=".h5")
    link_file = NamedTemporaryFile(delete_on_close=False, suffix=".h5")
    with src_file, link_file:
        # Create source data to copy
        with h5py.File(src_file, mode='w') as src_h5fd:
            src_h5fd['src_data'] = np.random.random((10, 20, 30))
        # Create a link to the source data
        link_file.close()
        with h5py.File(link_file.name, mode='w') as target_file:
            target_file['target_link'] = h5py.ExternalLink(src_file.name, '/src_data')
            target_file['target_link'].attrs['spam'] = 'eggs'
            assert isinstance(target_file.get('target_link', getlink=True), h5py.ExternalLink)
            harden_link(parent=target_file, link_path="target_link")
            assert isinstance(target_file.get('target_link', getlink=True), h5py.HardLink)
            assert len(target_file.keys()) == 1
