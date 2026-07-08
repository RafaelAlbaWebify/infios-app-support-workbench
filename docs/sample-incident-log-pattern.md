# INFIOS M7 - Log-Pattern Evidence Scenario

## Scenario

Checkout intermittently returns HTTP 500, and application logs show the same exception signature repeated during the incident window.

This scenario practices log-pattern evidence handling without collecting real production logs.

## Support focus

The goal is to separate:

- user-visible symptom: intermittent HTTP 500;
- endpoint: which operation or route fails;
- time window: first seen, last seen, and incident window;
- correlation: request/correlation IDs linking user reports to logs;
- repeated signature: exception class, message fingerprint, or stable error pattern;
- scope: one endpoint, one instance, one deployment version, one user segment, or all traffic;
- signal quality: primary failure evidence versus secondary noise, retries, warnings, or follow-on errors.

## Evidence to collect

- exact timestamp;
- endpoint or operation;
- HTTP status;
- correlation/request IDs;
- shortest representative log excerpt;
- exception class or error signature;
- occurrence count in the incident window;
- first seen and last seen timestamps;
- host/container/instance identifier;
- deployment version or recent change;
- affected user/business scope;
- normal baseline or previous known-good comparison if available.

## Safe boundaries

Do not collect real secrets, tokens, session IDs, personal data, raw customer data, or large production log dumps.

Before sharing logs, redact sensitive fields and keep excerpts short and representative.

## Interview explanation

> I added a log-pattern scenario because Application Support work often depends on reading logs without jumping to conclusions. I group repeated errors by timestamp, endpoint, correlation ID, exception signature, host or instance, and recent deployment window. Then I escalate with a short representative log excerpt, occurrence count, first/last seen timestamps, and the uncertainty: whether the pattern is the primary failure or secondary noise.
