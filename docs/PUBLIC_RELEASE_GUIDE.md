# Public Release Guide

Use this checklist before publishing changes to a public fork or package.

## Keep In The Repository

- generalized source code
- tests with fake or synthetic data
- examples that run without secrets
- public documentation
- package metadata
- license files

## Keep Out Of The Repository

- `.env` files
- API keys, auth files, tokens, private keys, and credentials
- private memory databases
- user-specific session logs
- raw chat transcripts
- local runtime state
- generated media
- model weights or adapters
- dependency caches and vendored package trees
- local machine paths and usernames
- persona-specific datasets or identity anchors

## Review Commands

Run tests:

```bash
python -m pytest
```

Search for common sensitive artifacts:

```bash
git ls-files
git grep -n -i -E "api[_-]?key|secret|credential|token|private[_-]?key|password"
git grep -n -i -E "local path|private memory|session log|chat transcript"
```

Check the staged file list before committing:

```bash
git status --short
git diff --cached --stat
git diff --cached --name-only
```

## Documentation Rule

When a guide needs an install path, use placeholders such as `<workspace>` or `<project-folder>`. Do not write personal local paths, usernames, emails, phone numbers, or machine-specific config.

## Publication Status Language

Prefer precise wording:

- "reference implementation"
- "sanitized snapshot"
- "example module"
- "local demo"

Avoid claims that imply unsupported maturity or deployment guarantees.
