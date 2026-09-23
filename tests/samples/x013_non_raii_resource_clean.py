"""RAII-compliant subprocess usage: ``Popen`` is always context managed."""

import subprocess


def run_echo() -> str:
    """Run a subprocess, ensuring the process handle is always closed."""
    with subprocess.Popen(["echo", "hello"]) as proc:
        proc.wait()
    return "done"
