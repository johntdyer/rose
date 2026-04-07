# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ROSE (Recursive Organizational Structure Extractor) is a single-file Python CLI that connects to an LDAP server and prints an org chart tree for a given user. It supports traversing down (directs) or up (reporting chain) the hierarchy.

## Commands

```bash
# Install dependencies (creates .venv)
uv sync

# Run linter
uv run flake8 rose.py

# Run the app locally (requires env vars set)
uv run rose.py <person>
uv run rose.py <person> --detailed
uv run rose.py <person> --directsonly
uv run rose.py <person> --reverse

# Build Docker image
make
```

## Required Environment Variables

All five must be set before running:

| Variable | Purpose |
|---|---|
| `ROSE_HOST` | LDAP server hostname |
| `ROSE_PORT` | LDAP server port |
| `ROSE_UNAME` | Bind username |
| `ROSE_PWORD` | Bind password |
| `ROSE_SEARCH_BASE` | LDAP search base DN |

## Architecture

All logic lives in `rose.py`. The flow is:

1. Parse CLI args via `docopt` (usage string at top of file acts as the spec)
2. Connect to LDAP using `ldap3` with TLS (certs from `certs/` in Docker, or system certs locally)
3. Look up the target person by `sAMAccountName` or email (`mail` attribute)
4. Recursively walk `directReports` (downward) or `manager` (upward), printing each entry with indentation

The `<person>` argument accepts either a `sAMAccountName` or an email address (detected by presence of `@`).

## Docker

Custom CA certificates go in `certs/*.crt` — they are baked into the image via `update-ca-certificates`. The image uses uv to install dependencies from `pyproject.toml`.
