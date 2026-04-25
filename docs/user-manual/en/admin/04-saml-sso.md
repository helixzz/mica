# SAML SSO

Mica supports SAML 2.0 integration with enterprise identity providers such as **ADFS** and **Microsoft Entra ID**.

## Key parameters

| Parameter | Meaning |
|:---|:---|
| `auth.saml.enabled` | enable or disable SAML sign-in |
| `auth.saml.idp.entity_id` | IdP Entity ID |
| `auth.saml.idp.sso_url` | IdP SSO URL |
| `auth.saml.idp.slo_url` | IdP logout URL |
| `auth.saml.idp.x509_cert` | IdP signing certificate |
| `auth.saml.attr.email` | email attribute mapping |
| `auth.saml.attr.display_name` | display name attribute mapping |
| `auth.saml.attr.groups` | group attribute mapping |

## ADFS setup summary

Use the following SP endpoints when creating the relying-party trust:

- ACS URL: `https://<your-domain>/api/v1/saml/acs`
- Entity ID: `https://<your-domain>/api/v1/saml/metadata`

Typical ADFS values:

- Entity ID: `http://adfs.yourcompany.com/adfs/services/trust`
- SSO URL: `https://adfs.yourcompany.com/adfs/ls/`

## Microsoft Entra ID setup summary

In the enterprise application SAML configuration:

- Identifier: `https://<your-domain>/api/v1/saml/metadata`
- Reply URL: `https://<your-domain>/api/v1/saml/acs`
- Sign-on URL: `https://<your-domain>/login`

## JIT provisioning and group mapping

Administrators can configure:

- default role
- default company code
- default department code
- group-to-role / department mapping rules in JSON

## Pre-enable checklist

- IdP metadata values are complete and correct
- the PEM certificate is complete
- the default company code exists in Mica
- the IdP-side ACS URL and Entity ID match the Mica configuration
