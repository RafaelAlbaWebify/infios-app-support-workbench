# Recent Case Dashboard

The guided interface now opens on a recent-case dashboard rather than forcing technicians to create a new incident every time.

## Supported workflow

1. Load up to 20 recently updated cases.
2. Show case title, application, affected scope, business impact, status, and last update time.
3. Open an existing case by mouse or keyboard.
4. Reload its persisted evidence and current case summary.
5. Continue adding evidence and refreshing guidance.
6. Return to the dashboard without creating a duplicate case.

## Safety and accessibility

- Unknown scope and impact remain explicit.
- Case cards are keyboard accessible using Enter or Space.
- The dashboard contains no production-changing action.
- Investigation logic remains in backend APIs; the browser only renders and submits structured data.
