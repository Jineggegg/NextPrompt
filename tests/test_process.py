import os
import subprocess
import sys
import time

import pytest

from nextprompt.process import run_process


def test_real_process_timeout_is_bounded():
    started = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        run_process([sys.executable, "-c", "import time; time.sleep(20)"], timeout=0.15)
    assert time.monotonic() - started < 5


def test_no_output_capture_for_daemonizing_clipboard_commands():
    result = run_process([sys.executable, "-c", "print('do not capture')"], capture_output=False)
    assert result.returncode == 0 and result.stdout == result.stderr == b""


@pytest.mark.skipif(os.name != "posix", reason="POSIX process-group behavior")
def test_timeout_kills_pipe_inheriting_descendant():
    # A surviving child inheriting stdout would keep communicate() blocked for 20s.
    script = (
        "import subprocess,sys,time;"
        "subprocess.Popen([sys.executable,'-c','import time;time.sleep(20)']);"
        "time.sleep(20)"
    )
    started = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        run_process([sys.executable, "-c", script], timeout=0.2)
    assert time.monotonic() - started < 5
