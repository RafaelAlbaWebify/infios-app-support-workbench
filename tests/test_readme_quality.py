from pathlib import Path


def _extract_code_blocks(markdown: str, language: str) -> list[str]:
    blocks: list[str] = []
    lines = markdown.splitlines()
    in_block = False
    current: list[str] = []

    for line in lines:
        if line.strip() == f"```{language}" and not in_block:
            in_block = True
            current = []
            continue

        if line.strip() == "```" and in_block:
            blocks.append("\n".join(current))
            in_block = False
            current = []
            continue

        if in_block:
            current.append(line)

    return blocks


def test_readme_powershell_blocks_contain_commands_only() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    powershell_blocks = _extract_code_blocks(readme, "powershell")

    assert powershell_blocks

    allowed_prefixes = (
        "python ",
        ".\\",
        "pip ",
        "pytest ",
        "uvicorn ",
        "infios ",
    )

    for block in powershell_blocks:
        for line in block.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            assert stripped.startswith(allowed_prefixes), f"Unexpected non-command line in PowerShell block: {stripped}"


def test_readme_demo_reports_are_not_inside_powershell_blocks() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    powershell_blocks = _extract_code_blocks(readme, "powershell")

    for block in powershell_blocks:
        for line in block.splitlines():
            stripped = line.strip()
            assert not stripped.startswith("reports/"), f"Report path leaked into PowerShell block: {stripped}"


def test_readme_has_demo_commands_and_reports_sections() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "## Demo Commands" in readme
    assert "## Demo Reports" in readme
    assert "samples/incident-sql-query-timeout.json" in readme
    assert "reports/sample-sql-query-timeout-report.md" in readme
