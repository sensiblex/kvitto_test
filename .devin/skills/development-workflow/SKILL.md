---
name: development-workflow
description: Control how changes are made in this repository. Use when implementing features, fixing bugs, refactoring, adding dependencies, or making commits in this project.
---

# Development Workflow Skill

## Purpose

Control how changes are made in this repository.

## Before Coding

Always:

1. Read the relevant existing files.
2. Identify the current implementation.
3. Identify related tests.
4. Identify the requirement being implemented.
5. Determine the smallest reasonable change.

Do not start coding from assumptions.

## During Coding

Implement one logical task at a time.

Do not combine unrelated features.

Do not rewrite the entire project unless explicitly requested.

Do not modify unrelated files.

## After Coding

Always:

1. inspect changed files;
2. check imports;
3. run relevant tests;
4. run the complete test suite when appropriate;
5. report failures honestly.

If tests fail, do not claim the task is complete.

## Dependency Changes

Before adding a dependency:

1. check whether the standard library or existing dependencies are sufficient;
2. determine whether the dependency is justified;
3. avoid adding dependencies for trivial functionality.

## Refactoring

Do not refactor working code while implementing an unrelated feature.

If refactoring is necessary:

1. explain why;
2. keep behavior unchanged;
3. run tests before and after.

## Git

Prefer small logical commits.

Suggested progression:

```text
init
database
tariffs
payment-logic
payment-api
idempotency
webhook
tests
documentation
review
```

Do not mix unrelated changes in one commit.

## Completion

Never say "done" merely because code was written.

A task is complete only when:

- implementation exists;
- tests pass;
- requirements are satisfied;
- no known blocking issue remains.
