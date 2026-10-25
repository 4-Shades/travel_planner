"""Scenarios of features/api/api_protection.feature (BDD scenarios §4.5); the steps are shared, in features/conftest.py.

"Only the web application and the Host are public" is @deployment and run by hand.
"""

from pytest_bdd import scenario

FEATURE = "api/api_protection.feature"


@scenario(FEATURE, "A key is required when HOST_API_KEY is set")
def test_key_required():
    pass


@scenario(FEATURE, "A missing key is reported before the body is checked")
def test_key_before_body():
    pass


@scenario(FEATURE, "A rejected request does not reveal the key")
def test_rejection_reveals_nothing():
    pass


@scenario(FEATURE, "No key is needed when HOST_API_KEY is not set")
def test_no_key_configured():
    pass
