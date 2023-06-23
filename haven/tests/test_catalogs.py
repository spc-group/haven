from haven.catalog import tiled_client


def test_tiled_client(sim_tiled):
    uri = sim_tiled.uri.split("/")[2]
    uri = f"http://{uri}"
    client = tiled_client(entry_node="255id_testing", uri=uri)
    assert "7d1daf1d-60c7-4aa7-a668-d1cd97e5335f" in client.keys()
    run = client["7d1daf1d-60c7-4aa7-a668-d1cd97e5335f"]
    assert run.metadata["start"]["plan_name"] == "xafs_scan"
