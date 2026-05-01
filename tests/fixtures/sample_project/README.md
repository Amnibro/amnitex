# sample_project

A tiny fixture project used by atex's MCP round-trip smoke tests.

The auth flow uses HMAC-SHA256 signed cookies issued by `auth.py`.
Database connections live in `db.py` and use a connection pool of size 8.
