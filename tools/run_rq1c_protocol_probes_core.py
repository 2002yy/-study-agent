"""Guarded loader for the reviewed deterministic RQ1-C protocol core.

The immutable core source is stored as a repository payload and verified against
its Git blob id before execution. Direct script execution always returns through
the public exact-head entrypoint before the core payload is loaded.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

if __name__ == "__main__":
    from tools.run_rq1c_protocol_probes import main as guarded_main

    raise SystemExit(guarded_main())

_PAYLOAD = Path(__file__).with_name("rq1c_protocol_probes_core_source.zip")
_file_sha = "6544ba7428981ac49f65ec1c2815e4320c66bd7d"
_source = _PAYLOAD.read_bytes()
_git_blob = b"blob " + str(len(_source)).encode("ascii") + b"\0" + _source
if hashlib.sha1(_git_blob).hexdigest() != _file_sha:
    raise RuntimeError("RQ1-C protocol core payload integrity mismatch")

exec(compile(_source, str(_PAYLOAD), "exec"), globals(), globals())
