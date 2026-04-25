# HTTPS / TLS

HTTPS is strongly recommended in production, especially when SAML SSO is enabled.

## Required certificate files

- `server.crt` — server certificate (bundle intermediate certificates if needed)
- `server.key` — matching private key

## Enable HTTPS

```bash
cd deploy
./scripts/enable-tls.sh --cert /path/to/server.crt --key /path/to/server.key
```

The script validates certificates, copies files into `deploy/certs/`, switches Nginx to HTTPS mode, restarts Nginx, and performs a smoke test.

## Revert to HTTP

```bash
./scripts/disable-tls.sh
```

## Renewal and port changes

- rerun `enable-tls.sh` with the new certificate pair when certificates are renewed
- change the HTTPS port in `deploy/.env` if required

## SSO note

If you manually configured SP Entity ID or ACS URL before enabling HTTPS, update them to `https://` values.
