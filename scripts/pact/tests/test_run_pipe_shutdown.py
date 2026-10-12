"""Regression tests for bounded PACT run pipe draining and interruption.

A grandchild can inherit both output pipes after the direct verification child
has exited or been terminated. In either case, PACT must not block indefinitely,
must not publish a passing receipt, and must leave unrelated descendants alone.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import time
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]
RUN = ROOT / "scripts" / "pact" / "run.py"


class RunPipeShutdownTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pact-run-pipe-")
        self.root = pathlib.Path(self.temp.name) / "project"
        self.root.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(
            ["git", "config", "user.name", "PACT Test"], cwd=self.root, check=True
        )
        subprocess.run(
            ["git", "config", "user.email", "pact@example.invalid"],
            cwd=self.root, check=True,
        )
        (self.root / "README.md").write_text("# pipe integration\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "baseline"], cwd=self.root, check=True)
        self.receipt = self.root / ".pact" / "runs" / "TASK-PIPE" / "receipt.json"
        self.grandchild_pid = pathlib.Path(self.temp.name) / "grandchild.pid"
        self.wrapper: subprocess.Popen[str] | None = None

    def tearDown(self) -> None:
        wrapper = self.wrapper
        if wrapper is not None:
            if os.name != "nt" and hasattr(os, "killpg"):
                # Each wrapper has a private POSIX session; clean only that
                # test-owned session so orphan grandchildren do not survive.
                try:
                    os.killpg(wrapper.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            elif self.grandchild_pid.exists():
                try:
                    pid = int(self.grandchild_pid.read_text(encoding="ascii"))
                    os.kill(pid, signal.SIGTERM)
                except (ValueError, OSError, ProcessLookupError):
                    pass
            if wrapper.poll() is None:
                wrapper.kill()
            try:
                wrapper.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                wrapper.kill()
                wrapper.communicate(timeout=5)
            if wrapper.stdout is not None:
                wrapper.stdout.close()
            if wrapper.stderr is not None:
                wrapper.stderr.close()
        self.temp.cleanup()

    def start(
        self, *, hold_direct_child: bool, grandchild_sleep: float = 30.0
    ) -> subprocess.Popen[str]:
        # Spawn a descendant that intentionally retains both output pipe
        # handles and does not itself print. Direct child either exits at
        # once or waits for termination from PACT.
        grandchild = f"import time; time.sleep({grandchild_sleep!r})"
        child = (
            "import pathlib,subprocess,sys,time\n"
            "p=subprocess.Popen([sys.executable,'-c',"
            + repr(grandchild)
            + "], stdin=subprocess.DEVNULL, stdout=sys.stdout, stderr=sys.stderr)\n"
            f"pathlib.Path({str(self.grandchild_pid)!r}).write_text(str(p.pid), encoding='ascii')\n"
            "sys.stdout.write('direct-child-output\\n');sys.stdout.flush()\n"
            + ("time.sleep(30)\n" if hold_direct_child else "")
        )
        self.wrapper = subprocess.Popen(
            [
                sys.executable, str(RUN), "--task-id", "TASK-PIPE",
                "--output", str(self.receipt), "--cwd", str(self.root),
                "--quiet", "--", sys.executable, "-c", child,
            ],
            cwd=self.root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=os.name != "nt",
        )
        return self.wrapper

    def await_grandchild(self) -> None:
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline and not self.grandchild_pid.exists():
            if self.wrapper is not None and self.wrapper.poll() is not None:
                break
            time.sleep(0.03)
        self.assertTrue(self.grandchild_pid.exists(), "descendant did not become ready")

    def test_descendant_closing_pipes_within_grace_can_publish_success(self) -> None:
        wrapper = self.start(hold_direct_child=False, grandchild_sleep=0.2)
        self.await_grandchild()
        out, err = wrapper.communicate(timeout=8)
        self.assertEqual(wrapper.returncode, 0, out + err)
        self.assertTrue(self.receipt.is_file(), err)
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertEqual(receipt["status"], "pass")
        self.assertEqual(
            receipt["stdout_sha256"],
            hashlib.sha256(b"direct-child-output\n").hexdigest(),
        )

    def test_direct_child_exit_cannot_wait_forever_for_descendant_pipe_eof(self) -> None:
        wrapper = self.start(hold_direct_child=False)
        self.await_grandchild()
        out, err = wrapper.communicate(timeout=8)
        self.assertEqual(wrapper.returncode, 2, out + err)
        self.assertIn("output streams", err)
        self.assertFalse(self.receipt.exists(), "unbounded output must not create a receipt")

    @unittest.skipIf(
        os.name == "nt" or not hasattr(os, "killpg"),
        "process-only SIGINT delivery is POSIX-specific",
    )
    def test_interrupt_only_pact_returns_130_with_inherited_descendant_pipes(self) -> None:
        wrapper = self.start(hold_direct_child=True)
        self.await_grandchild()
        # Unlike a terminal-wide Ctrl-C, this signal reaches *only* PACT.
        # Descendants keep the output pipe handles open.
        os.kill(wrapper.pid, signal.SIGINT)
        out, err = wrapper.communicate(timeout=8)
        self.assertEqual(wrapper.returncode, 130, out + err)
        self.assertIn("PACT run: interrupted", err)
        self.assertNotIn("Traceback", err)
        self.assertFalse(self.receipt.exists())


if __name__ == "__main__":
    unittest.main()
