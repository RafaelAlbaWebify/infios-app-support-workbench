# INFIOS architecture

INFIOS is a local-first modular monolith: one Python application, one SQLite database and five browser surfaces.

## Runtime

```text
Browser -> FastAPI -> domain validation -> repository -> SQLite
CLI or Windows launcher -> same FastAPI application
```

## Main boundaries

| Area | Responsibility |
|---|---|
| `app/main.py` | Application composition and route registration |
| `app/api/` | HTTP endpoints and browser routes |
| `app/models.py` | Domain validation rules |
| `app/repository.py` | SQLite persistence and queries |
| `app/ui/` | HTML, CSS and modular browser JavaScript |
| `app/cli.py` | Analysis and local server entrypoint |
| `tools/` | Windows launch, validation and packaging |
| `tests/` | Unit, API, persistence, packaging and browser proof |

## Operator surfaces

| Route | Purpose |
|---|---|
| `/` | Incident investigation and escalation |
| `/problems` | Problems, actions and known-error guidance |
| `/handovers` | Immutable shift snapshots |
| `/catalogue` | Services, ownership and dependencies |
| `/analytics` | Descriptive operational summaries |

All browser surfaces use backend models; presentation controls do not replace server validation.

## Stored records

SQLite persists cases, evidence, observations, diagnostic actions, explanations, recovery checks, escalation packages, services, dependencies, case links, handovers, problems, corrective actions and known-error records.

Automated tests cover restart persistence, representative bulk data, repeated imports and concurrent reads.

## Packaging

The same application runs through:

- editable development installation;
- repository-local Windows bootstrap;
- a wheel installed outside the checkout;
- a versioned Windows ZIP with a package-local launcher.

The Windows ZIP creates a private `.runtime` environment and stores its default database under `data`.

## Delivery proof

Each completed change is validated on its exact pull-request head through Python, Chromium Playwright and Windows bootstrap/persistence/export jobs. The tested SHA is then squash-merged and compared with `main`.

## Scope

The portfolio-ready local-first scope intentionally excludes multi-user hosting, authentication, automated remediation, tenant-wide discovery, high availability and external ticketing integrations.
