---
name: payment-business-logic
description: Use this skill when implementing or reviewing payment calculations, promo codes, installment schedules, idempotency, or status transitions.
---

# Payment Business Logic Skill

## Purpose

Use this skill when implementing or reviewing payment calculations, promo codes, installment schedules, idempotency, or status transitions.

## Money

All monetary values are integer kopecks.

Never use float for money.

Example:

```text
19 900 ₽ = 1 990 000 kopecks
```

Calculations must use integer arithmetic.

## Promo Code

Required promo code:

```text
KVITTO10
```

Discount:

```text
10%
```

Matching is case-insensitive.

Unknown promo codes must produce validation error 422.

## Installment Schedule

Allowed periods:

```text
3
6
12
```

The sum of all schedule entries must exactly equal the payment amount.

Use integer division:

```text
base = amount // months
remainder = amount % months
```

The first `remainder` payments receive `base + 1`.

All remaining payments receive `base`.

Example:

```text
1 990 000 / 3

base = 663 333
remainder = 1

schedule =
[663334, 663333, 663333]
```

Invariant:

```text
sum(schedule) == amount
```

This invariant must be tested.

## Payment Statuses

Allowed transitions:

```text
pending -> succeeded
pending -> failed
succeeded -> refunded
```

All other transitions are invalid.

An invalid transition must not mutate the payment.

## Idempotency

For POST /payments:

First request with a new Idempotency-Key:

```text
201
```

Repeated request with the same key:

```text
200
```

The same payment must be returned.

No duplicate payment may be created.

The database must enforce uniqueness.

## Design Principle

Keep these rules in independently testable service functions.

Do not duplicate the same business logic in multiple route handlers.
