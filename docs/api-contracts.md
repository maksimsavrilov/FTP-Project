# Shared API Schemas and Authentication Client Contract

This document defines the first shared HTTP contract between Master and the
independent Authentication Service. It defines wire-level data only; it does
not define the Authentication Service implementation or Master API handlers.

## Common HTTP rules

- All endpoints use JSON and the `/v1` URL prefix.
- Request and response field names use `snake_case`.
- Identifiers are opaque strings. Clients must not infer their format.
- Timestamps are RFC 3339 UTC strings, for example `2026-01-01T00:00:00Z`.
- A client must treat unknown response fields as forward-compatible additions.
- An unsuccessful response uses the `ApiError` schema unless the transport
  fails before an HTTP response is available.

## Shared schemas

### ApiError

```json
{
  "code": "AUTHORIZATION_DENIED",
  "message": "The principal is not allowed to perform this action.",
  "request_id": "req-7f8c"
}
```

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `code` | string | yes | Stable machine-readable error code. |
| `message` | string | yes | Human-readable diagnostic, not a decision key. |
| `request_id` | string | yes | Correlates the response with service logs. |
| `details` | object | no | Safe, structured error-specific data. |

### Principal

```json
{
  "subject_id": "user-123",
  "subject_type": "USER",
  "scopes": ["service:read", "service:write"],
  "expires_at": "2026-01-01T01:00:00Z"
}
```

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `subject_id` | string | yes | Authenticated identity identifier. |
| `subject_type` | string | yes | Identity category, initially `USER` or `SERVICE`. |
| `scopes` | array of strings | yes | Effective scopes for the presented credential. |
| `expires_at` | timestamp | no | Credential expiry, when applicable. |

### AuthorizationDecision

```json
{
  "allowed": true,
  "principal": {
    "subject_id": "user-123",
    "subject_type": "USER",
    "scopes": ["service:read", "service:write"],
    "expires_at": "2026-01-01T01:00:00Z"
  },
  "request_id": "req-7f8c"
}
```

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `allowed` | boolean | yes | Whether the requested action is authorized. |
| `principal` | Principal | yes when `allowed` is true | Identity and effective scopes. |
| `request_id` | string | yes | Correlation identifier. |

A valid credential with `allowed: false` is an authorization denial. An invalid
or expired credential is an authentication failure and is returned as HTTP
`401`; it is not represented as an allowed decision.

## Authentication Service endpoint

### Start user login

`GET /v1/login`

The CLI opens this endpoint in a user agent. The service responds with HTTP
`302` to ZITADEL's `/oauth/v2/authorize` endpoint using the configured client,
callback URI, `response_type=code`, and `openid profile email` scopes. A caller
may provide an opaque `state`; otherwise the service generates one. The state
is returned unchanged by the callback and must be checked by the CLI.

The callback URI is configured as `AUTH_LOGIN_REDIRECT_URI` and defaults to
`http://localhost:8001/v1/login/callback` for the local Compose stack.

### Complete user login

`GET /v1/login/callback?code=<authorization-code>&state=<state>`

The service exchanges the one-time code at ZITADEL's token endpoint and
returns HTTP `200` with the token response, including `access_token`,
`token_type`, and any `refresh_token` or `expires_in` supplied by ZITADEL. The
response also includes `state` when it was supplied and `request_id` for
correlation. OAuth errors are returned as `401 AUTHENTICATION_FAILED`; missing
codes are `400 INVALID_REQUEST`; token endpoint failures are
`503 AUTH_SERVICE_UNAVAILABLE`.

### Authorize a Master request

`POST /v1/authorize`

The Master sends the end-user credential in the standard `Authorization` header
and asks the Authentication Service to evaluate one action. The Authentication
Service validates the access token with ZITADEL introspection before evaluating
its scopes. The credential is not copied into the JSON body or persisted by
Master.

Request headers:

```text
Authorization: Bearer <credential>
X-Request-ID: req-7f8c
```

Request body:

```json
{
  "resource": "service:service-123",
  "action": "write",
  "context": {
    "tenant_id": "tenant-456"
  }
}
```

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `resource` | string | yes | Resource identifier in `type:id` form. |
| `action` | string | yes | Requested operation, such as `read` or `write`. |
| `context` | object | no | Additional authorization attributes. |

Successful response: HTTP `200` with `AuthorizationDecision`.

## HTTP failure contract

| Status | Error code | Master client behavior |
| --- | --- | --- |
| `400` | `INVALID_REQUEST` | Do not retry; surface a contract/configuration error. |
| `401` | `AUTHENTICATION_FAILED` | Reject the caller and do not retry with the same credential. |
| `403` | `AUTHORIZATION_DENIED` | Reject the operation without retrying. |
| `429` | `RATE_LIMITED` | Retry only according to `Retry-After`. |
| `500`/`502`/`503`/`504` | `AUTH_SERVICE_UNAVAILABLE` | Treat as a dependency failure; bounded retry is allowed for idempotent authorization checks. |

## Master Authentication Client contract

The Master client is the only Master component that calls the Authentication
Service. API handlers depend on the client interface, not on an HTTP library or
an Authentication Service data model.

Conceptual interface:

```text
authorize(
    credential: str,
    resource: str,
    action: str,
    context: object | null,
) -> AuthorizationDecision
```

The client must:

- send the credential only in the `Authorization` header;
- propagate or create `X-Request-ID` for correlation;
- validate the response against `AuthorizationDecision` and `ApiError`;
- return the principal only after `allowed` is true;
- map transport failures and `5xx` responses to a dependency failure;
- apply bounded timeouts and bounded retries only to transient failures;
- never retry `400`, `401`, `403`, or a malformed response;
- never cache authorization decisions beyond the credential expiry unless a
  separate policy explicitly permits it;
- never persist credentials or forward them to Worker Agents.

No hosting state is changed by this call. Master remains responsible for
applying business rules and persisting the resulting desired state after the
authorization check succeeds.

## CLI Master HTTP client contract

The CLI uses an authenticated `MasterClient` for business-resource operations.
The client accepts a persisted `UserSession`, sends its credential only as
`Authorization: Bearer <access_token>`, and propagates or generates an
`X-Request-ID` for every request. `GET` reads a resource and `POST` creates a
resource using the JSON body returned by the Master API.

HTTP responses with an `ApiError` body are raised as a structured client error
with the status, stable error code, message, and request ID. Transport failures
and malformed JSON are raised as unavailable/invalid-response client errors.
The client does not persist credentials, retry requests, or call Worker Agents.
