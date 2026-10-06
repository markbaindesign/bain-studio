import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Keep test runs out of the real studio/sync.log: sync.py opens its log at import.
os.environ["SYNC_LOG"] = os.path.join(tempfile.mkdtemp(prefix="sync-log-"), "sync.log")
