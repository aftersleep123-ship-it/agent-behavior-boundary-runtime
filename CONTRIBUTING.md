# Contributing

Contributions should keep this repository generic, inspectable, and free of private runtime data.

## Good Changes

- documentation improvements
- focused tests
- small boundary-control improvements
- clearer examples with fake data
- portability fixes

## Changes To Avoid

- private memory exports
- chat logs
- local runtime state
- generated media
- model weights or adapters
- service credentials
- personal local paths or usernames
- persona-specific datasets

## Before Opening A Pull Request

```bash
python -m pytest
git status --short
git diff --stat
```

Also review `SECURITY_PUBLIC_CHECK.md` and `docs/PUBLIC_RELEASE_GUIDE.md`.
