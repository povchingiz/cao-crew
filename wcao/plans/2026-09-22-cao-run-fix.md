# Fix: `cao-run` crash — `HERE: unbound variable`

**Date:** 2026-09-22  
**Status:** ✅ Done

## Problem
Running `cao-run` crashed immediately with:
```
/Users/yerta/.local/bin/cao-run: line 24: HERE: unbound variable
```

## Root Cause
`set -euo pipefail` was set at the top of the script (activating `-u` — strict unbound variable checking).  
`$HERE` was referenced on **line 24** (inside `_CFG="$HERE/../2_configure/..."`)  
but the block that *defines* `HERE` via symlink resolution was placed **10 lines later**.

## Fix Applied
**File:** `/Users/yerta/.local/bin/cao-run`

Moved the `SELF`/`HERE` symlink-resolution block to immediately after `set -euo pipefail`, so `HERE` is always defined before it is used.

```bash
# BEFORE (broken order):
set -euo pipefail
_CFG="$HERE/..."        # ← HERE used but not yet set ❌
...
HERE="$(cd ...)"        # ← defined too late

# AFTER (fixed order):
set -euo pipefail
SELF="${BASH_SOURCE[0]}"
while [ -L "$SELF" ]; do ... done
HERE="$(cd "$(dirname "$SELF")" && pwd)"   # ← defined first ✅
_CFG="$HERE/..."        # ← now safe
```

## Verification
Re-run `cao-run` from the terminal — it should no longer crash at startup.
