"""Run from an installed plugin without pip installation."""

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nextprompt.cli import main  # noqa: E402

raise SystemExit(main())
