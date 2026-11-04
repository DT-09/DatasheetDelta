# DatasheetDelta 1.0 release gate

No public release, release tag, launch announcement or production-readiness claim is permitted until every mandatory gate below is evidenced.

## Product behavior
- [ ] Supported document formats and extraction contract are explicit and tested.
- [ ] Tables, repeated labels, merged cells, multi-column layouts and document reading order have documented behavior.
- [ ] Scanned PDF handling is either implemented and tested or clearly excluded from 1.0.
- [ ] Unit conversions are dimension-safe, tested at boundaries and preserve original source values.
- [ ] Matching ambiguity is surfaced; no silent duplicate overwrite or guessed semantic equivalence.
- [ ] Every finding links to enough source context for a reviewer to verify it.
- [ ] Empty, malformed, encrypted, corrupt and unsupported documents fail safely with actionable errors.

## Review and traceability
- [x] Reviewer decisions and notes are implemented for a trusted single-operator deployment.
- [x] Review events are append-only through the application and linked by a SHA-256 hash chain.
- [x] Reports export machine findings separately from human review events.
- [ ] Reviewer identity is authenticated per person; self-entered reviewer names are not sufficient for multi-user approval.
- [ ] Retention, deletion, backup and restore behavior is validated under operational conditions.
- [ ] Review-history integrity is tested against corruption and documented database-administrator limitations.

## Security and privacy
- [x] Upload extension allowlisting and per-file size limits are implemented.
- [ ] Parser isolation, archive expansion limits and malicious-document tests are complete.
- [ ] No path traversal, unsafe archive expansion, formula injection or HTML injection is possible through supported flows.
- [ ] Rate limiting, encrypted storage, token rotation and secret-management procedures are documented and tested.
- [ ] Dependency and container vulnerability checks are clean or formally dispositioned.

## Quality and usability
- [ ] Automated tests cover supported formats and realistic document variations.
- [ ] API integration tests and browser end-to-end tests pass across supported browsers.
- [ ] Keyboard navigation, responsive behavior and accessible status communication are verified.
- [ ] CLI, API, UI and report outputs agree on findings and review decisions.
- [ ] Clean install and container build pass from a fresh environment.

## Validation and release operations
- [ ] Representative documents have been tested with engineering reviewers.
- [ ] Known extraction misses and false-positive modes are measured and disclosed.
- [ ] No unsupported accuracy, savings, compliance or customer claims appear in the product.
- [ ] Deployment guide, backup/restore and incident response notes are complete.
- [ ] Final release candidate passes the full CI matrix and a documented manual acceptance run.
- [ ] Product owner explicitly approves the single public 1.0 release.

A checked box requires evidence in the repository or a recorded validation artifact. Intention is not evidence.
