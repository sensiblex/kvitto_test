---
name: task-specification
description: Use this skill when analyzing the original test assignment, checking implementation against requirements, or deciding whether a feature belongs to the task.
---

# Task Specification Skill

## Purpose

Use this skill when analyzing the original test assignment, checking implementation against requirements, or deciding whether a feature belongs to the task.

## Rules

The original assignment is the source of truth.

Before implementing a feature:

1. Identify the exact requirement.
2. Determine whether it is mandatory or optional.
3. Identify expected input.
4. Identify expected output.
5. Identify expected HTTP status.
6. Identify business rules.
7. Check whether the requested behavior is already implemented.

Do not invent requirements.

Do not add production-grade functionality merely because it is common in payment systems.

## Mandatory Core Features

The core assignment requires:

- FastAPI;
- Pydantic v2;
- SQLite or PostgreSQL;
- SQLAlchemy or another ORM;
- GET /tariffs;
- POST /payments;
- GET /payments/{id};
- POST /webhooks/bank;
- integer kopecks for money;
- three predefined tariffs;
- KVITTO10 promo code;
- card/sbp/installment payment methods;
- installment periods 3/6/12;
- exact installment totals;
- payment statuses and valid transitions;
- Idempotency-Key;
- pytest + httpx;
- README;
- AI_LOG.md.

## Optional Features

Only after core functionality is complete:

- Docker Compose;
- webhook HMAC;
- Alembic;
- GET /payments filters;
- GitHub Actions;
- assistant configuration files.

## Conflict Resolution

If a proposed implementation conflicts with the assignment:

1. stop;
2. identify the conflict;
3. prefer the assignment;
4. explain the decision.

Never silently change business behavior.
