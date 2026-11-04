# Security policy

## Reporting a vulnerability

Do not publish sensitive vulnerability details in a public issue. Contact the repository owner through GitHub's private vulnerability reporting feature if enabled. If it is unavailable, use a private channel already published by the repository owner.

Include the affected version or commit, impact, reproduction conditions and any relevant logs with secrets removed.

## Current security scope

DatasheetDelta is in development and is not approved for confidential or regulated document processing. The API supports extension allowlisting, per-file size limits and an optional shared bearer token. Persisted reports contain extracted parameter values and source excerpts even though original documents are not retained.

The current token model does not provide individual identities, roles, SSO or per-user authorization. SQLite hash chaining detects ordinary changes to review events but cannot prevent a database administrator from rewriting the database. Deleting an investigation removes its complete report and review history.

This is not a substitute for a hardened parser sandbox, rate limiting, malware scanning, dependency monitoring, encrypted storage, backup controls or deployment-level access restrictions. Do not expose an unreviewed development deployment to untrusted users.
