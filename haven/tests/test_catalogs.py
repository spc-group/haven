from haven.catalog import tiled_client


def test_tiled_client(sim_tiled):
    client = tiled_client()
    assert "255id_testing" in client.keys()
    runs = client['255id_testing']
    assert "7d1daf1d-60c7-4aa7-a668-d1cd97e5335f" in runs.keys()
    run = runs["7d1daf1d-60c7-4aa7-a668-d1cd97e5335f"]
    assert run.metadata["start"]["plan_name"] == "xafs_scan"
