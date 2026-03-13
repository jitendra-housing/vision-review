# Common PR Review Guidelines

Universal code review standards for all platforms (iOS, Android, Web, Backend).

---

## Use Your Full Intelligence

These guidelines define format, style, and severity thresholds. They do **not** limit your review scope.

Apply your full knowledge of security, architecture, performance, correctness, and language idioms. Flag issues even if they don't match a documented rule — good engineering judgment takes precedence over any checklist. Think like a senior engineer who has seen these bugs in production.

---

## Severity Levels

- **HIGH** — Security vulnerabilities, crashes, data loss, architecture violations, race conditions, breaking changes. Must be fixed before merge.
- **MEDIUM** — Maintainability issues, missing tests, convention violations, performance concerns, missing error handling. Should be fixed.
- **LOW** — Style preferences, minor improvements, documentation gaps. Fix if easy, otherwise track separately.

**Assumption-based findings:** When a finding depends on an assumption about data, call flow, or runtime behavior that is not visible in the diff, lower severity by one level (HIGH → MEDIUM) and state the assumption explicitly in the problem description.

**Prioritize in this order:**
1. Security (injection, auth bypass, secrets, input validation)
2. Architecture (DI violations, module boundaries, circular deps)
3. Data integrity (transactions, race conditions, migrations)
4. Correctness (business logic, edge cases, idempotency)
5. Everything else

---

## Database Migrations

Migration files run against production databases under load. Review them with extreme caution.

### Lock-Hazardous DDL (flag as HIGH)

- **`CREATE INDEX`** without `CONCURRENTLY` — takes `ACCESS EXCLUSIVE` lock, blocks all reads and writes until complete.
- **`ADD CONSTRAINT`** without `NOT VALID` — scans entire table while holding an exclusive lock. Use `NOT VALID` first, then `VALIDATE CONSTRAINT` separately (takes only `ShareUpdateExclusiveLock`).
- **`ALTER COLUMN TYPE`** — triggers a full table rewrite + exclusive lock. Use the expand/contract pattern: add a shadow column with the new type, backfill, swap.
- **`ADD COLUMN WITH DEFAULT`** (pre-PG 11) — rewrites entire table. Even on PG 11+, verify the version before assuming this is safe.

### Migration Hygiene

- **Never mix schema changes and data backfills** in the same migration. Data migrations can time out or fail partway, leaving schema changes partially applied. Run data backfills as separate, idempotent scripts or background jobs.
- **Migrations are immutable once applied.** Never edit an already-applied migration. Flyway will throw a checksum mismatch; Active Record won't error but creates dangerous drift between environments. Always create a new migration to correct a previous one.
- **Data migrations** that do `UPDATE ... SET` on an entire table must be batched. A single transaction touching millions of rows locks the table and can fill the WAL/binlog.
- **Irreversible migrations** (column drops, type changes that lose data) must be flagged as HIGH. Verify a rollback path exists.

---

## Comment Style Rules

Every comment must be a **definitive finding** — state what IS wrong and what the correct approach IS.

**Never use:**
- "Verify that...", "Ensure that...", "Make sure...", "Check if..."
- "Consider...", "You might want to...", "It might be worth..."
- "Potentially", "Appears to", "Seems like", "Could possibly"

**Every comment must include:**
1. What the problem is
2. Why it matters (consequence in production)
3. How to fix it (concrete code or specific steps)

If you cannot write a comment as a definitive assertion, skip it. False positives are worse than missed issues.

**Exception — operational and deployment risks:** If a code change introduces a well-known operational hazard (e.g. DDL that locks tables, missing index on a foreign key, unbounded query, unsafe migration pattern), flag it even if you cannot verify the runtime impact from the diff alone. State your assumption explicitly and use HIGH severity. These risks are too costly to miss.

---

## Output Format

Each finding uses this structure:

```
**[SEVERITY] Category — Short Title**
`path/to/file.ext` line N

❌ **Problem:** One sentence stating what is wrong and why it matters in production.
```language
// the bad code
```

✅ **Fix:** One sentence stating the correct approach.
```language
// the correct code
```
```

**Example:**

---

**[HIGH] Security — SQL Injection**
`api/users.py` line 45

❌ **Problem:** User input is concatenated directly into the SQL query — any attacker can read or destroy the entire database.
```python
query = f"SELECT * FROM users WHERE name = '{user_input}'"
```

✅ **Fix:** Use a parameterized query so the database driver handles escaping.
```python
cursor.execute("SELECT * FROM users WHERE name = ?", (user_input,))
```

---

**For findings without a code fix** (e.g. missing tests, architectural issues), omit the code blocks and use plain text for the Fix section.

Group findings by severity: all HIGH first, then MEDIUM, then LOW.

---

## Priority Hierarchy

When conflicts arise between guideline sources:

1. **Platform-specific guidelines** (iOS.md, Android.md, etc.) — project conventions
2. **This file** — universal standards and format
3. **Your engineering knowledge** — applies everywhere, especially for production risks not covered above. Do not wait for a guideline to flag a known hazard.
