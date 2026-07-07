# INFIOS Incident Report - INFIOS-SAMPLE-403-AFTER-LOGIN

## Incident Summary

Customer Portal is reporting 'The user enters valid credentials, login succeeds, but the portal returns HTTP 403 Forbidden when opening the dashboard.'. This is being treated as an Application Support case with evidence-first analysis.

## User Impact

One user can authenticate but cannot access the Customer Portal dashboard. Business impact is limited until role or group scope is confirmed.

## Incident Metadata

| Field | Value |
|---|---|
| Title | User receives HTTP 403 after successful login |
| Service | Customer Portal |
| Environment | sample |
| HTTP Status | 403 |
| Endpoint | /dashboard |
| Correlation ID | sample-corr-20260707-104500-def456 |

## Evidence Table

| Source | Timestamp | Confidence | Detail |
|---|---:|---|---|
| user report | 2026-07-07T10:45:00+02:00 | medium | User reports valid credentials are accepted, then the dashboard returns HTTP 403 Forbidden. |
| browser observation | 2026-07-07T10:47:00+02:00 | high | HTTP 403 observed on /dashboard after successful login and redirect. |
| application log sample | 2026-07-07T10:47:03+02:00 | medium | Sample log references correlation ID sample-corr-20260707-104500-def456 and authorization denied while checking dashboard permission. |
| identity note | 2026-07-07T10:49:00+02:00 | medium | Authentication appears successful; application authorization still needs role, group, or claim validation. |

## Findings

| Category | Severity | Statement | Evidence References |
|---|---|---|---|
| Access control | high | The symptom indicates an authentication or authorization boundary. Separate credential validation, session/token creation, role mapping, and application permission checks. | http_status, symptom, endpoint |
| Authorization | high | HTTP 403 usually means the user is authenticated but the application denies access to the requested resource. | http_status, endpoint |
| Login flow | medium | The symptom occurs around login, so authentication, session creation, user profile loading, and post-login authorization should be separated. | title, symptom |
| Traceability | info | A correlation ID is available and should be used to find exact server-side log entries. | correlation_id |
| Evidence | info | 4 evidence item(s) were provided for initial analysis. | user report, browser observation, application log sample, identity note |
| Recent changes | medium | Recent changes exist and should be compared with the incident start time. | recent_changes |

## Likely Causes - Not Confirmed

- User is authenticated but missing the required application role, group membership, claim, or permission.
- Application role mapping or authorization rule is stale, misconfigured, or recently changed.
- The requested route or resource is restricted to a different role, tenant, site, or business unit.
- Mismatch between identity provider groups/claims and application authorization rules.
- Recent access-control or deployment change affecting the post-login route.

## Unknowns

- Exact failure point in the login, access, or dependency flow.
- Whether the issue affects all users or only a subset.
- Whether the error is reproducible from another browser, device, or network.

## Missing Evidence

- Identity provider sign-in evidence showing whether authentication succeeded.
- Application authorization log entry for the failed endpoint and user.
- Expected role/group/app-permission evidence for the affected resource.
- Comparison with a known working user in the same business role.

## Safe Next Steps

- Confirm whether credentials are accepted before the access error appears.
- Compare the affected user with a known working user in the same role and business context.
- Collect application authorization logs around the timestamp and endpoint.
- Check identity provider sign-in/authentication evidence separately from application authorization evidence.
- Verify expected group membership, app role assignment, claims, tenant/site scope, and route permission.
- Do not add permissions or change groups until the required access model is confirmed by the application owner.
- Map the flow stage precisely: credential validation, callback/session creation, landing page, then protected resource access.
- Do not restart services or modify data without evidence and approval.
- Prepare escalation with impact, timestamps, endpoint, correlation ID, reproduction steps, and collected logs.
- Keep user-facing updates factual: impact, workaround if known, and next investigation step.

## Escalation Note

Please investigate incident INFIOS-SAMPLE-403-AFTER-LOGIN: User receives HTTP 403 after successful login. Impact: One user can authenticate but cannot access the Customer Portal dashboard. Business impact is limited until role or group scope is confirmed. Observed symptom: The user enters valid credentials, login succeeds, but the portal returns HTTP 403 Forbidden when opening the dashboard. HTTP status: 403. Endpoint: /dashboard. Correlation ID: sample-corr-20260707-104500-def456. Requested support: review application logs, identity/session evidence, and dependency calls around the incident timestamp, then confirm the failing component or access rule.

## RCA Draft

RCA draft: The confirmed root cause is not yet known. Current evidence shows an access-control failure visible to the user during or after login. Next RCA update should confirm whether authentication succeeded, which authorization rule denied access, the affected user scope, the corrective action, and the preventive control.

## Support Boundary

This report is evidence-first. It does not confirm root cause without logs, dependency evidence, or owner validation.
