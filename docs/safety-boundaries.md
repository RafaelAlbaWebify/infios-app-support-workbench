# INFIOS Safety Boundaries

INFIOS is a local-first Application Support Engineering workbench for portfolio practice and safe support reasoning.

## Allowed

- Use public-safe sample incidents.
- Analyze JSON evidence supplied by the operator.
- Generate structured incident summaries.
- Generate escalation notes.
- Generate RCA drafts with uncertainty clearly marked.
- Run locally on a developer workstation.

## Not Allowed

- Connecting to real production systems.
- Storing credentials, tokens, secrets, or customer data.
- Modifying databases.
- Restarting services.
- Auto-remediating incidents.
- Claiming confirmed root cause without evidence.
- Presenting the operator as a full developer, DBA, SRE, or security specialist.

## Support Principle

INFIOS should help an Application Support Engineer say:

> Based on the evidence, this is what we know, this is what we do not know, this is the safest next check, and this is what we need from the owning team.
