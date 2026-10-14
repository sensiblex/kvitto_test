---
name: fastapi-development
description: Use this skill when creating or modifying FastAPI routes, dependencies, request schemas, and response schemas.
---

# FastAPI Development Skill

## Purpose

Use this skill when creating or modifying FastAPI routes, dependencies, request schemas, and response schemas.

## Principles

Use standard FastAPI patterns.

Prefer:

- APIRouter;
- Pydantic v2 models;
- dependency injection for database sessions;
- explicit response models;
- HTTPException where appropriate;
- type hints.

Avoid unnecessary abstractions.

## Routes

Required routes:

```text
GET  /tariffs
POST /payments
GET  /payments/{id}
POST /webhooks/bank
```

Routes should remain thin.

Route handlers should coordinate:

```text
request
  ↓
validation
  ↓
service/business logic
  ↓
database
  ↓
response
```

Do not place large business algorithms directly inside endpoint functions.

## Validation

Use Pydantic for input validation.

Use FastAPI's standard 422 response for validation errors.

Do not create custom validation response formats unless required.

## HTTP Status Codes

Use the codes specified by the assignment.

Important cases:

```text
POST /payments
201 — newly created
200 — existing payment returned through Idempotency-Key

GET /payments/{id}
200 — found
404 — not found

POST /webhooks/bank
200 — successful transition
404 — payment not found
409 — invalid transition
```

Do not invent alternative status codes without a reason.

## API Responses

Payment responses must contain:

```text
id
status
tariff_id
amount
discount
method
installment_months
schedule
email
created_at
```

Keep response schemas explicit.
