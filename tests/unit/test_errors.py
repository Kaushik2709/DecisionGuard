import pickle

from decisionguard.domain.errors import GuardError


def test_domain_error_survives_process_transport():
    error = pickle.loads(pickle.dumps(GuardError("BUSY", "Retry the same request")))
    assert isinstance(error, GuardError)
    assert error.code == "BUSY" and error.message == "Retry the same request"
    assert str(error) == "Retry the same request"
