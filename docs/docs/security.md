# Security

This page summarizes the security-relevant aspects of the Dataset Profiler service.

## Authentication

The API supports optional token-based authentication, toggled with the
`ENABLE_AUTH` environment variable.

- When `ENABLE_AUTH=false` (the default), the endpoints are accessible without a token.
- When `ENABLE_AUTH=true`, every profiler endpoint requires a JWT supplied as a
  Bearer token in the `Authorization` header.

The service decodes the JWT **without verifying its signature** and only checks
that the `client_id` claim equals `airflow`. Requests with a missing or malformed
token are rejected with `401 Unauthorized`; valid tokens whose `client_id` is not
`airflow` are rejected with `403 Forbidden`.

See the [Configuration](configuration.md#authentication) section for the expected
token payload and more details.

!!! warning "Signature verification"

    The current implementation does not verify the JWT signature; it trusts the
    upstream gateway to do so. Authentication should therefore be relied upon only
    behind a trusted gateway that performs full token validation.

## Transport

The service is intended to be deployed behind the DataGEMS platform gateway, which
terminates TLS and handles external exposure. See [Deployment](deployment.md).

## Secrets & Configuration

Credentials (database, Redis, SCAYLE, etc.) are provided through environment
variables and must not be committed to the repository. See
[Configuration](configuration.md#environment-variables) for the full list.
