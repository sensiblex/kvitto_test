---
name: code-review
description: Use this skill when reviewing implementation before considering a task complete.
---

# Code Review Skill

## Purpose

Use this skill when reviewing implementation before considering a task complete.

## Review Priority

Review in this order:

### 1. Business correctness

Check:

- money calculations;
- promo code;
- installments;
- status transitions;
- idempotency.

### 2. Data integrity

Check:

- integer money fields;
- database constraints;
- unique Idempotency-Key;
- state mutation;
- transaction boundaries.

### 3. API correctness

Check:

- endpoint paths;
- request validation;
- response schemas;
- HTTP status codes;
- error responses.

### 4. Tests

Check:

- required scenarios;
- result assertions;
- state assertions;
- test isolation;
- regression coverage.

### 5. Code quality

Check:

- type hints;
- readability;
- function size;
- duplication;
- unnecessary abstractions;
- unnecessary dependencies.

## Review Rules

Do not praise code without evidence.

Report concrete issues.

For every issue provide:

```text
Severity:
File:
Problem:
Why it matters:
Recommended fix:
```

Severity:

- CRITICAL — incorrect business behavior, data corruption, security problem;
- MAJOR — requirement violation or significant bug;
- MINOR — maintainability or style issue.

Do not recommend refactoring merely for stylistic preference.

## Interview Check

For important code, ask:

- Can the developer explain why this exists?
- Can the developer explain the algorithm?
- Can the developer modify it during a live interview?
- Is the implementation simpler than necessary, or unnecessarily complicated?

Prefer code that can be explained clearly during a Junior-level technical interview.
