# Sample Incident - HTTP 500 After Login

## Scenario

A user reports that credentials are accepted, but immediately after login the application returns HTTP 500.

## Application Support Interpretation

HTTP 500 means the server failed while processing the request. It does not identify the root cause alone.

For a login-flow incident, the failure may happen in different stages:

1. Credential validation.
2. Identity provider callback.
3. Session creation.
4. User profile or role loading.
5. Downstream dependency call.
6. Portal landing page rendering.

## Evidence to Collect

- Exact timestamp.
- Affected user or role.
- Endpoint or route.
- HTTP status.
- Correlation ID or request ID.
- Browser/network observation.
- Application log entry.
- Recent deployment/configuration changes.
- Dependency health: database, identity provider, API, cache, or message queue.

## Safe Support Next Steps

- Reproduce with a test user if available.
- Compare affected and working users.
- Check if the issue affects one user, one role, one site, or all users.
- Search application logs by correlation ID.
- Escalate with evidence, not guesses.

## Natural Interview Explanation

> For HTTP 500 after login, I would avoid jumping directly to root cause. I would first separate whether login itself is failing or whether the error happens after authentication. I would collect timestamp, endpoint, HTTP status, correlation ID, affected user scope, and any recent changes. Then I would check logs around that request and escalate with a clear evidence package if the failing component is owned by development or a vendor.
