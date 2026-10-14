# Kvitto Payment API — AI Development Context

## 1. Project Overview

This repository contains a test assignment for a Junior Python Developer position.

The task is to implement a small payment API for an online school using FastAPI.

The application must provide:

- tariff listing;
- payment creation;
- payment retrieval;
- bank webhook for payment status changes;
- promo code support;
- installment payment schedules;
- payment status transitions;
- idempotent payment creation;
- automated tests.

The implementation must prioritize correctness, simplicity, readability, and testability.

The goal is not to build a production-scale payment platform.

---

## 2. Source of Truth

The original test assignment is the primary source of truth.

Do not silently change, reinterpret, weaken, or extend its requirements.

When a requirement is unclear:

1. inspect the original task;
2. inspect the existing implementation;
3. identify the ambiguity;
4. choose the simplest reasonable solution;
5. document the decision if it affects behavior.

Do not invent business rules that are not present in the assignment.

Do not add functionality merely because it is common in production systems.

---

## 3. Required Technology Stack

Use:

- Python 3.11+
- FastAPI
- Pydantic v2
- SQLAlchemy
- SQLite
- pytest
- httpx

Docker and Alembic are not required for the core implementation.

PostgreSQL is allowed by the assignment, but SQLite should be preferred unless there is a concrete reason to use PostgreSQL.

Do not introduce additional frameworks or infrastructure without a clear reason.

---

## 4. Required API

The core API consists of four endpoints:

### GET /tariffs

Returns available tariffs.

Response items contain:

- id
- title
- price

---

### POST /payments

Creates a payment.

Request fields:

- tariff_id
- email
- method
- installment_months
- promo_code

Supported payment methods:

- card
- sbp
- installment

For installment payments, `installment_months` is required and may only be:

- 3
- 6
- 12

A newly created payment has status:

`pending`

The endpoint normally returns HTTP 201.

If the same `Idempotency-Key` was already used, the existing payment must be returned with HTTP 200 and no new payment must be created.

---

### GET /payments/{id}

Returns a payment by ID.

Existing payment:

`200 OK`

Unknown payment:

`404 Not Found`

---

### POST /webhooks/bank

Receives a payment status update from the bank.

Request fields:

- payment_id
- status

Unknown payment:

`404 Not Found`

Invalid status transition:

`409 Conflict`

Response:

```json
{
  "error": "invalid_transition"
}
```

The payment status must not change when the transition is invalid.

Successful transition:

```json
{
  "result": "ok"
}
```

with HTTP 200.

---

## 5. Money Rules

Money is always represented as an integer number of kopecks.

Example:

`19 900 ₽ = 1 990 000`

Never use `float` for monetary values.

Do not introduce floating-point arithmetic into payment calculations.

Prefer integer arithmetic.

---

## 6. Tariffs

Tariffs must exist when the application starts.

Required tariffs:

| Title | Price in rubles | Price in kopecks |
|---|---:|---:|
| basic | 9 900 | 990 000 |
| standard | 19 900 | 1 990 000 |
| premium | 29 900 | 2 990 000 |

Initialization must not create duplicate tariffs when the application starts multiple times.

---

## 7. Promo Code

The only required promo code is:

`KVITTO10`

It gives a 10% discount.

Promo code matching is case-insensitive.

These values must behave identically:

- KVITTO10
- kvitto10
- Kvitto10
- KvItTo10

An unknown promo code must result in HTTP 422.

Do not create a database table for promo codes unless there is a concrete reason.

The required behavior can be implemented simply.

---

## 8. Installments

Installment periods:

- 3 months
- 6 months
- 12 months

The total of all schedule entries must be exactly equal to the payment amount.

Remainders must be distributed to the first payments.

Example:

```text
1 990 000 / 3

[663334, 663333, 663333]
```

because:

```text
663334 + 663333 + 663333 = 1 990 000
```

Never lose or create kopecks because of rounding.

A suitable integer-based algorithm is:

```text
base = amount // months
remainder = amount % months

first `remainder` payments = base + 1
remaining payments = base
```

Dates for installment payments are not required.

---

## 9. Payment Statuses

Allowed transitions:

```text
pending -> succeeded
pending -> failed
succeeded -> refunded
```

All other transitions are invalid.

Invalid transitions must:

- return HTTP 409;
- return `{"error": "invalid_transition"}`;
- leave the current status unchanged.

Status transition logic should be isolated from the HTTP layer and be independently testable.

---

## 10. Idempotency

`POST /payments` supports the `Idempotency-Key` HTTP header.

Behavior:

### First request

```text
Idempotency-Key: abc-123
```

No existing payment has this key.

Result:

- create payment;
- return HTTP 201.

### Repeated request

```text
Idempotency-Key: abc-123
```

A payment with this key already exists.

Result:

- do not create another payment;
- return the existing payment;
- return HTTP 200.

The database should enforce uniqueness of the idempotency key.

Do not rely only on an application-level `if exists` check.

---

## 11. Payment Response

Payment responses must contain:

- id
- status
- tariff_id
- amount
- discount
- method
- installment_months
- schedule
- email
- created_at

`schedule` is:

- a list of integer kopeck amounts for installment payments;
- `null` for non-installment payments.

---

## 12. Validation

Use Pydantic v2 for request validation.

Use FastAPI's standard validation error format.

Do not create a custom global validation-error format unless the assignment explicitly requires it.

Validation should reject invalid input as early as practical.

Examples:

- invalid payment method;
- invalid installment period;
- missing installment period for installment payment;
- invalid promo code.

---

## 13. Architecture Principles

Keep the project simple.

Prefer separation into:

```text
API layer
    ↓
Service / business logic
    ↓
Database layer
```

Business rules should not be buried inside route handlers when they can be expressed as independent functions.

Examples of logic that should be independently testable:

- payment amount calculation;
- promo code calculation;
- installment schedule calculation;
- status transition validation.

Do not create unnecessary abstractions such as:

- repositories for every model;
- generic service factories;
- excessive interfaces;
- dependency injection frameworks;
- event buses;
- CQRS;
- microservices.

This is a small test assignment.

---

## 14. Database

Use SQLAlchemy.

SQLite is sufficient for the core task.

Important constraints should be represented at the database level where appropriate.

At minimum, `idempotency_key` must be unique.

Avoid storing structured data in the database in unnecessarily complicated forms.

If `schedule` is stored as JSON, use a clear and consistent representation.

Do not introduce a separate database table for every small concept unless the assignment requires it.

---

## 15. Testing Requirements

Use:

- pytest
- httpx

Tests must verify behavior, not merely HTTP status codes.

Required scenarios include:

1. payment amount without promo code;
2. payment amount with promo code;
3. promo code in lowercase;
4. installment schedule for 3 months;
5. installment schedule for 6 months;
6. installment schedule for 12 months;
7. schedule total equals payment amount;
8. repeated Idempotency-Key does not create a duplicate;
9. invalid status transition returns 409;
10. invalid transition does not modify status;
11. nonexistent payment returns 404.

Tests should be isolated from each other.

Prefer fixtures for database setup and cleanup.

---

## 16. Development Workflow

Do not implement the whole project in one step.

Work incrementally:

1. analyze requirements;
2. design architecture;
3. create project skeleton;
4. implement database;
5. implement tariffs;
6. implement money/business logic;
7. test business logic;
8. implement Pydantic schemas;
9. implement payment creation;
10. implement idempotency;
11. implement payment retrieval;
12. implement status transitions;
13. implement bank webhook;
14. add integration tests;
15. audit against the specification;
16. fix discovered issues;
17. prepare README;
18. prepare AI_LOG.md;
19. perform final review.

After every meaningful stage:

- run tests;
- check imports;
- inspect changed files;
- avoid leaving broken intermediate code.

---

## 17. Change Discipline

Before modifying code:

1. inspect the relevant files;
2. understand the existing implementation;
3. identify dependencies;
4. make the smallest reasonable change.

Do not rewrite unrelated files.

Do not refactor working code without a concrete reason.

Do not introduce new dependencies without justification.

When fixing a bug, add or update a test that reproduces the problem.

---

## 18. AI Behavior

The AI is an implementation assistant, not the source of truth.

The AI must:

- inspect existing code before changing it;
- follow the original specification;
- explain non-obvious decisions;
- avoid unnecessary complexity;
- verify generated code;
- run tests after changes;
- report uncertainty instead of inventing requirements.

The AI must not assume that generated code is correct.

If an implementation decision affects business behavior, explain it before or alongside the change.

---

## 19. Do Not Overengineer

This project is evaluated as a Junior Python / FastAPI test assignment.

Do not optimize for enterprise architecture.

Do not add:

- authentication;
- frontend;
- real bank integration;
- deployment;
- unnecessary Docker configuration;
- unnecessary migrations;
- background workers;
- message brokers;
- Redis;
- Celery;
- Kubernetes;
- microservices.

These are outside the core requirements.

---

## 20. Optional Bonuses

Only implement bonuses after all core requirements work and tests pass.

Possible bonuses:

- Docker Compose;
- webhook HMAC-SHA256 signature validation;
- Alembic migrations;
- GET /payments with email/status filters;
- GitHub Actions with Ruff and pytest;
- project-specific AI instructions.

Do not sacrifice core correctness for bonus features.

---

## 21. Code Quality

Prefer:

- explicit type hints;
- small functions;
- descriptive names;
- simple control flow;
- clear validation;
- standard FastAPI patterns;
- readable SQLAlchemy models;
- deterministic tests.

Avoid:

- cryptic abbreviations;
- huge functions;
- deeply nested conditionals;
- duplicated business logic;
- unnecessary comments;
- comments that merely restate the code.

Code should be understandable by a Junior Python developer during a technical interview.

---

## 22. Interview Readiness

The developer must be able to explain every important part of the implementation.

Pay special attention to:

- why money uses integers;
- how the installment algorithm works;
- why the remainder goes to the first payments;
- how Idempotency-Key works;
- why database uniqueness is important;
- how invalid status transitions are prevented;
- why business logic is separated from routes;
- how tests isolate the database;
- why particular HTTP status codes are returned.

Do not generate code that cannot be reasonably explained during an interview.

---

## 23. Final Definition of Done

The project is not considered complete until:

- the application starts from the README instructions;
- all required endpoints work;
- all required business rules work;
- money is handled only as integer kopecks;
- installment totals are exact;
- idempotency works;
- status transitions work;
- invalid transitions return 409 without changing state;
- missing payments return 404;
- required tests pass;
- README is complete;
- AI_LOG.md is present;
- the implementation has been reviewed against the original assignment.

Only after this should optional bonuses be considered.
