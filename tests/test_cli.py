import json

from flake8_lint.cli import main


def test_cli_version(capsys) -> None:
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == "1.0.0"


def test_cli_check_json_reports_violation(tmp_path, capsys) -> None:
    sample = tmp_path / "sample.py"
    sample.write_text(
        "def handler() -> int:\n"
        '    """Handle a broad exception."""\n'
        "    try:\n"
        "        risky()\n"
        "    except Exception:\n"
        "        return 1\n",
        encoding="utf-8",
    )
    assert main(["check", str(sample), "--select", "X002", "--output-format", "json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["violations"][0]["code"] == "X002"
