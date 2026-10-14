---
name: testing
description: Use this skill when writing, reviewing, or debugging tests.
---

# Testing Skill

## Purpose

Use this skill when writing, reviewing, or debugging tests.

## Stack

Use:

- pytest
- httpx

## Testing Philosophy

Tests must verify behavior and results.

A test that only checks:

```python
response.status_code == 200
```

is usually insufficient.

Verify response data and state changes.

## Required Business Tests

Cover:

### Money

- normal payment amount;
- discounted payment;
- lowercase promo code;
- invalid promo code.

### Installments

- 3 months;
- 6 months;
- 12 months;
- exact schedule sum;
- remainder distribution.

### Idempotency

- first request creates payment;
- repeated key returns same payment;
- repeated key does not create another payment;
- first response is 201;
- repeated response is 200.

### Statuses

- valid transitions;
- invalid transitions;
- invalid transition returns 409;
- invalid transition does not modify state.

### Resources

- existing payment returns 200;
- missing payment returns 404.

## Test Isolation

Tests must not depend on execution order.

Use fixtures for test database setup and cleanup.

Do not use the production database for tests.

## Regression Rule

When a bug is found:

1. reproduce it with a test;
2. fix the implementation;
3. ensure the new test passes;
4. run the complete test suite.

## Final Check

Before declaring a task complete:

```bash
pytest
```

must pass.
