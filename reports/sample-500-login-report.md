# INFIOS Incident Report - INFIOS-SAMPLE-500-LOGIN

## Incident Summary

Customer Portal is reporting 'After entering valid credentials, the user is redirected to the portal landing page and receives HTTP 500 Internal Server Error.'. This is being treated as an Application Support case with evidence-first analysis.

## User Impact

One user cannot access the portal after login. Business impact is limited until more affected users are confirmed.

## Incident Metadata

| Field | Value |
|---|---|
| Title | User receives HTTP 500 after login |
| Service | Customer Portal |
| Environment | sample |
| HTTP Status | 500 |
| Endpoint | /auth/callback |
| Correlation ID | sample-corr-20260707-091500-abc123 |

## Evidence Table

| Source | Timestamp | Confidence | Detail |
|---|---:|---|---|
| user report | 2026-07-07T09:15:00+02:00 | medium | User reports valid credentials are accepted, then the portal returns a generic HTTP 500 page. |
| browser observation | 2026-07-07T09:17:00+02:00 | high | HTTP 500 observed on /auth/callback after successful credential submission. |
| application log sample | 2026-07-07T09:17:03+02:00 | medium | Sample log references correlation ID sample-corr-20260707-091500-abc123 and exception while loading user profile after login. |

## Findings

| Category | Severity | Statement | Evidence References |
|---|---|---|---|
| HTTP | high | HTTP 500 indicates the server failed while processing the request. It does not prove root cause by itself. | http_status, symptom |
| Login flow | medium | The symptom occurs around login, so authentication, session creation, user profile loading, and post-login authorization should be separated. | title, symptom |
| Traceability | info | A correlation ID is available and should be used to find exact server-side log entries. | correlation_id |
| Evidence | info | 3 evidence item(s) were provided for initial analysis. | user report, browser observation, application log sample |
| Recent changes | medium | Recent changes exist and should be compared with the incident start time. | recent_changes |

## Likely Causes - Not Confirmed

- Unhandled application exception during or after login.
- Backend dependency failure after authentication, such as database, identity, session, or downstream API.
- Configuration or deployment issue affecting the login callback or post-login route.

## Unknowns

- Exact failure point in the login or access flow.
- Whether the issue affects all users or only a subset.
- Whether the error is reproducible from another browser, device, or network.

## Missing Evidence

- Database or dependency health evidence, if login loads profile/session data.

## Safe Next Steps

- Reproduce the login flow with a sample or test user if available.
- Collect exact timestamp, endpoint, HTTP status, browser observation, and correlation ID.
- Check application logs around the timestamp for exception class, stack trace, and failed dependency.
- Compare affected user scope: one user, one role, one site, or all users.
- Confirm whether credentials are accepted before the error appears.
- Check whether the failure happens before login, at callback, after callback, or after landing page load.
- Compare one affected user with a known working user with the same role.
- Do not restart services or modify data without evidence and approval.
- Prepare escalation with impact, timestamps, endpoint, correlation ID, reproduction steps, and collected logs.
- Keep user-facing updates factual: impact, workaround if known, and next investigation step.

## Escalation Note

Please investigate incident INFIOS-SAMPLE-500-LOGIN: User receives HTTP 500 after login. Impact: One user cannot access the portal after login. Business impact is limited until more affected users are confirmed. Observed symptom: After entering valid credentials, the user is redirected to the portal landing page and receives HTTP 500 Internal Server Error. HTTP status: 500. Endpoint: /auth/callback. Correlation ID: sample-corr-20260707-091500-abc123. Requested support: review application logs, identity/session evidence, and dependency calls around the incident timestamp, then confirm the failing component or access rule.

## RCA Draft

RCA draft: The confirmed root cause is not yet known. Current evidence shows an application-side failure visible to the user during the login flow. Next RCA update should confirm the failing component, trigger, blast radius, resolution, and preventive action after logs and dependency evidence are reviewed.

## Support Boundary

This report is evidence-first. It does not confirm root cause without logs, dependency evidence, or owner validation.
