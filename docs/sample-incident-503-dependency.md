# INFIOS M3 - HTTP 503 Dependency Unavailable

## Scenario

The application loads, but a specific operation returns HTTP 503 Service Unavailable because a required downstream dependency is unavailable, degraded, timing out, or failing health checks.

The sample case uses order submission failing because the Inventory API dependency is unhealthy.

## Support focus

This scenario expands INFIOS from login and access triage into dependency and service-health triage.

The goal is to separate:

- application availability: is the main application reachable?
- operation failure: which action fails?
- dependency boundary: which downstream service, API, database, queue, cache, or integration is involved?
- failure mode: unavailable, degraded, timeout, rate limit, circuit breaker, DNS, TLS, firewall, routing, deployment, or configuration.
- blast radius: one user, one operation, all users, one site, one integration path, or one dependency owner scope.

## Evidence to collect

- exact timestamp;
- endpoint or operation;
- HTTP status;
- correlation/request ID;
- application log entry;
- dependency name;
- dependency health check or monitoring state;
- recent deployment/configuration/maintenance changes;
- connectivity evidence if the dependency is external or cross-service;
- known workaround or unaffected operation if available.

## Safe boundaries

Do not restart services, change routes, modify data, clear queues, or change dependency configuration without evidence and approval.

## Interview explanation

> I added an HTTP 503 dependency scenario because Application Support work is not only about login errors. Sometimes the application is reachable, but a specific operation fails because a dependency is unhealthy. In that case I separate the main app from the downstream dependency, collect correlation ID and health evidence, check recent changes, and escalate with the failing dependency and impact clearly described.
