import pytest

TEST_CERT = (
    "-----BEGIN CERTIFICATE-----"
    "MIIEFTCCAv2gAwIBAgIQF8tLz6onD4iJ4MkM0F7f6DANBgkqhkiG9w0BAQsFADCB"
    "gTELMAkGA1UEBhMCQ0gxGTAXBgNVBAoTEE1vY2sgQ2VydGlmaWNhdGUgQ28xKTAn"
    "BgNVBAsTIE1vY2sgQ2VydGlmaWNhdGUgQXV0aG9yaXR5IFJvb3QxJDAiBgNVBAMT"
    "G01vY2sgQ2VydGlmaWNhdGUgUm9vdCBDQTAeFw0yNTAxMDEwMDAwMDBaFw0zNTAx"
    "MDEwMDAwMDBaMIGBMQswCQYDVQQGEwJDSDEZMBcGA1UEChMQTW9jayBDZXJ0aWZp"
    "Y2F0ZSBDbzEpMCcGA1UECxMgTW9jayBDZXJ0aWZpY2F0ZSBBdXRob3JpdHkgUm9v"
    "dDEkMCIGA1UEAxMbTW9jayBDZXJ0aWZpY2F0ZSBSb290IENBMIIBIjANBgkqhkiG"
    "9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0ly8ubWvRazS4HOXEusGIE2jkTBxyqTRqAl4"
    "k7lcy8XTur2qxGn8pY/+bexdFv+DE5jBqFaUG2yygxN6E466+vWXTjhBMWrMUR3N"
    "MPvMXxMvmP0xSg6u40qCMgfHdCqkfNNpJBWlAbIYW/W2PASi6DPd7OJbRRqtD9h5"
    "uvvZk90un0nLBKBPXn1HULICwhf66A1VpzwuWdlxeqmoeZaZX6mE6oPD58Ll35H5"
    "BrZEcD3xKhsR4HIX66vepQP9enZ5bY3bT5iAG2wE8xmPKzW0fvkYlEYwH14r2raU"
    "unlslqY5T2r8j04YfGLwRoTSesFiNUFDXL9uBeb5GsyhQOdE31QIDAQABo1MwUTAd"
    "BgNVHQ4EFgQU6mE6xPD58Ll35H5BrZEcD3xKhsQwHwYDVR0jBBgwFoAU6mE6xPD5"
    "8Ll35H5BrZEcD3xKhsQwDwYDVR0TAQH/BAUwAwEB/zANBgkqhkiG9w0BAQsFAAOC"
    "AQEAIbT59uD3gTWMukYdR4P9J66yUfX2KF1be9JY3zhge36QTtf8l0oob8cMY3A6"
    "0EYh3YOEoTP0TO+cdMKx+3CX6X1cxZV8oPZxC25f6/sOlne342XQI3/OQvPsvBLn"
    "H2m6q+UpBAkLTlaX2UjsFvdcGaVbL50DJBSSTXobHxPPH/FkOFjHlkRQAt2bQVWw"
    "ycYzaO+VxDRKCVh0b07XHtcwPa5RWPLXxI75PwQxzb62LF8A3+yQUwSWOSJyYwcm"
    "WV7k/akdUSHh3D1ynjUTduVdJN9WewtG/XAIN5e8wZsM+dAf5BgU984wgKLF6igQ"
    "X4Jt9V7H5PHeTtQKgHdwNwp0UrEGnw=="
    "-----END CERTIFICATE-----"
)


async def _enable_saml(seeded_client):
    admin_login = await seeded_client.post(
        "/api/v1/auth/login/json",
        json={"username": "admin", "password": "MicaDev2026!"},
    )
    admin_token = admin_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}
    updates = {
        "auth.saml.enabled": True,
        "auth.saml.idp.entity_id": "https://adfs.example.com/adfs/services/trust",
        "auth.saml.idp.sso_url": "https://adfs.example.com/adfs/ls/",
        "auth.saml.idp.x509_cert": TEST_CERT,
    }
    for key, value in updates.items():
        response = await seeded_client.put(
            f"/api/v1/admin/system-params/{key}",
            headers=headers,
            json={"value": value},
        )
        assert response.status_code == 200, response.text


async def _set_admin_param(seeded_client, key: str, value):
    admin_login = await seeded_client.post(
        "/api/v1/auth/login/json",
        json={"username": "admin", "password": "MicaDev2026!"},
    )
    admin_token = admin_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await seeded_client.put(
        f"/api/v1/admin/system-params/{key}",
        headers=headers,
        json={"value": value},
    )
    assert response.status_code == 200, response.text


@pytest.mark.integration
async def test_login_options_reports_saml_disabled_by_default(seeded_client):
    response = await seeded_client.get(
        "/api/v1/auth/login-options",
        headers={"Accept-Language": "en-US"},
    )

    assert response.status_code == 200
    assert response.json() == {"saml_enabled": False, "saml_login_url": None}


@pytest.mark.integration
async def test_login_options_reports_saml_login_url_when_enabled(seeded_client):
    await _enable_saml(seeded_client)

    response = await seeded_client.get(
        "/api/v1/auth/login-options",
        headers={"Accept-Language": "en-US"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "saml_enabled": True,
        "saml_login_url": "/api/v1/saml/login",
    }


@pytest.mark.integration
async def test_saml_login_returns_503_when_disabled(seeded_client):
    await _set_admin_param(seeded_client, "auth.saml.enabled", False)
    response = await seeded_client.get(
        "/api/v1/saml/login",
        headers={"Accept-Language": "en-US"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "SAML single sign-on is not enabled"


@pytest.mark.integration
async def test_saml_login_redirects_to_idp_when_enabled(seeded_client):
    await _enable_saml(seeded_client)

    response = await seeded_client.get(
        "/api/v1/saml/login",
        headers={"Accept-Language": "en-US"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith("https://adfs.example.com/adfs/ls/")
    assert "SAMLRequest=" in location


@pytest.mark.integration
async def test_saml_login_returns_500_when_enabled_but_misconfigured(seeded_client):
    admin_login = await seeded_client.post(
        "/api/v1/auth/login/json",
        json={"username": "admin", "password": "MicaDev2026!"},
    )
    admin_token = admin_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}
    for key, value in {
        "auth.saml.enabled": True,
        "auth.saml.idp.entity_id": "https://adfs.example.com/adfs/services/trust",
        "auth.saml.idp.sso_url": "https://adfs.example.com/adfs/ls/",
        "auth.saml.idp.x509_cert": "",
    }.items():
        response = await seeded_client.put(
            f"/api/v1/admin/system-params/{key}",
            headers=headers,
            json={"value": value},
        )
        assert response.status_code == 200, response.text

    response = await seeded_client.get(
        "/api/v1/saml/login",
        headers={"Accept-Language": "en-US"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "SAML configuration is incomplete or invalid"


@pytest.mark.integration
async def test_local_login_still_works_when_saml_enabled(seeded_client):
    await _enable_saml(seeded_client)

    response = await seeded_client.post(
        "/api/v1/auth/login/json",
        json={"username": "alice", "password": "MicaDev2026!"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert set(payload) == {"access_token", "token_type", "expires_in"}
    assert payload["token_type"] == "bearer"
