import re
import sys
import tomllib
from importlib.metadata import distribution, version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_packaging_pins_extras_and_future_entrypoint():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    project = config["project"]
    assert sys.version_info[:2] == (3, 11)
    required = {item.split("==")[0] for item in project["dependencies"]}
    assert required == {"pydantic", "typer", "streamlit", "openai", "pypdf"}
    extras = project["optional-dependencies"]
    assert {item.split("==")[0] for item in extras["dev"]} == {"pytest", "ruff"}
    assert {item.split("==")[0] for item in extras["ocr"]} == {"pytesseract", "pillow"}
    for item in [*project["dependencies"], *extras["dev"], *extras["ocr"]]:
        assert re.fullmatch(r"[a-z]+==\d+(?:\.\d+)+", item), item
    for item in [*project["dependencies"], *extras["dev"]]:
        name, pinned = item.split("==")
        assert version(name) == pinned
    assert project["scripts"] == {"recoup": "recoup.cli:app"}
    entrypoint = next(
        entry
        for entry in distribution("recoup").entry_points
        if entry.group == "console_scripts" and entry.name == "recoup"
    )
    assert entrypoint.value == "recoup.cli:app"


def test_bootstrap_docs_and_index():
    expected = {
        "design/01-functional-design.md",
        "design/02-technical-design.md",
        "design/03-review-resolution.md",
        "specs/006-charles-contracts-world-fixtures.md",
        "specs/007-sonny-engine.md",
        "specs/008-carter-workbench-bench.md",
        "harness/SESSION-TEMPLATE.md",
        "harness/AGENTS-root.md",
        "harness/AGENTS-engine.md",
        "harness/AGENTS-ui-bench.md",
    }
    index = (ROOT / "docs/INDEX.md").read_text()
    for name in expected:
        assert f"]({name})" in index
        content = (ROOT / "docs" / name).read_text()
        assert content and "<!-- FILE:" not in content
    assert (ROOT / "AGENTS.md").read_bytes() == (ROOT / "docs/harness/AGENTS-root.md").read_bytes()
