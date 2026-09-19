"""Tests for the built-in help command (issue #1).

Runs the CLI as a subprocess on a clean environment to prove that help
works without Reddit credentials and that invalid commands still fail.
"""

import subprocess
import sys
import unittest

CMD = [sys.executable, "reddit_reader.py"]


def run(*args):
    return subprocess.run(CMD + list(args), capture_output=True, text=True, env={})


class HelpTest(unittest.TestCase):
    def test_dash_dash_help_exits_zero(self):
        r = run("--help")
        self.assertEqual(r.returncode, 0, r.stderr)
        for word in ("auth", "subs", "hot", "comments", "comment", "help"):
            self.assertIn(word, r.stdout)

    def test_help_command_exits_zero(self):
        r = run("help")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("usage:", r.stdout)

    def test_invalid_command_nonzero(self):
        r = run("bogus-command")
        self.assertNotEqual(r.returncode, 0)

    def test_no_args_nonzero(self):
        r = run()
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
