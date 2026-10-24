# Medical Device POC - Agent Instructions

This is a Python/Django proof-of-concept platform for tracking medical device boxes and instrument quantities.

## Working Rules

- Keep the project offline-first and Windows-friendly.
- Use Django templates and minimal vanilla JavaScript for the UI.
- Use PostgreSQL/EnterpriseDB as the only database target.
- Keep business rules in service modules, not views or models.
- Do not implement permissions beyond Django login until explicitly requested.
- Do not add export, printing, QR image generation, containerization, queue workers, or recovery mechanisms unless requested.
- Preserve the A/B port model:
  - Port A: inbound and review.
  - Port B: outbound.
- External scanner/input software communicates through PostgreSQL submission tables only.

## Implementation Style

- Prefer small, explicit Django apps over a single large app.
- Use database transactions and row locks for submission processing.
- Treat invalid QR code as data error with no operation record.
- Treat invalid state or quantity mismatch as business failure with operation record and report details.
- Keep table and field names in English; user-facing text can be Chinese.
