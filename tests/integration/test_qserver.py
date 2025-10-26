def test_qserver_open_environment(qserver):
    status = qserver.api.status()
    assert status["worker_environment_exists"]
