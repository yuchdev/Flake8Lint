"""Sample file demonstrating X013 non-RAII subprocess/socket usage violation."""

import subprocess


def run_echo() -> str:
    """Run a subprocess without managing its lifetime via ``with``."""
    proc = subprocess.Popen(["echo", "hello"])  # X013 - not context managed
    proc.wait()
    return "done"
