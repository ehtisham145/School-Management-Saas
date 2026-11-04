import pytest
from django.db import OperationalError

URL = "/api/health/"


class BrokenConnection:
    def cursor(self):
        raise OperationalError("could not connect: secret-host")


@pytest.mark.django_db
def test_health_is_ok_without_signing_in(api_client):
    response = api_client.get(URL)

    assert response.status_code == 200
    assert response.data == {"status": "oK"}


def test_health_is_503_when_the_database_is_down(api_client, monkeypatch):
    monkeypatch.setattr("apps.core.selectors.connection", BrokenConnection())

    response = api_client.get(URL)

    assert response.status_code == 503
    assert response.data == {"status": "unavailable"}


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_health_only_answers_get(api_client, method):
    assert getattr(api_client, method)(URL).status_code == 405
