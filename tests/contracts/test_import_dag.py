"""Enforce design/02 §2, including imports below module scope."""

import ast
from importlib.util import resolve_name
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PACKAGE_EDGES = {
    "contracts": {"contracts"},
    "world": {"world", "contracts"},
    "engine": {"engine", "contracts"},
    "app": {"contracts", "world", "engine"},
    "cli": {"cli", "contracts", "app"},
    "ui": {"ui", "contracts", "app"},
    "bench": {"bench", "contracts", "app"},
}
TEST_EDGES = {
    "contracts": {"contracts"},
    "world": {"contracts", "world", "app", "cli"},
    "app": {"contracts", "world", "app", "cli"},
    "cli": {"contracts", "world", "app", "cli"},
    "engine": {"contracts", "engine", "app"},
    "ui": {"contracts", "app", "ui"},
    "bench": {"contracts", "app", "bench"},
}


def violations(source: str, path: Path) -> list[str]:
    tree = ast.parse(source)
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    parts = path.parts
    is_test = parts[0] == "tests"
    area = parts[1].removesuffix(".py")
    allowed = (TEST_EDGES if is_test else PACKAGE_EDGES).get(area, set())
    package = list(parts[:-1])
    importlib_names = {"importlib"}
    builtins_names = {"builtins"}
    dynamic_names = {"__import__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            importlib_names.update(
                alias.asname or alias.name for alias in node.names if alias.name == "importlib"
            )
            builtins_names.update(
                alias.asname or alias.name for alias in node.names if alias.name == "builtins"
            )
        if isinstance(node, ast.ImportFrom):
            if node.module in {"importlib", "builtins"}:
                dynamic_names.update(
                    alias.asname or alias.name
                    for alias in node.names
                    if alias.name in {"import_module", "__import__"}
                )
    errors = []

    def check(module: str, node: ast.AST):
        if module != "recoup" and not module.startswith("recoup."):
            return
        target = module.split(".")[1] if "." in module else ""
        if target not in allowed:
            errors.append(f"{node.lineno}: forbidden edge to {module}")
        if not is_test and area == "app" and target == "engine":
            current = node
            in_build = False
            while current in parents:
                current = parents[current]
                if (
                    isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and current.name == "build"
                ):
                    in_build = True
            if module != "recoup.engine.factory" or not in_build:
                errors.append(
                    f"{node.lineno}: engine import must be recoup.engine.factory inside build"
                )

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                check(alias.name, node)
        elif isinstance(node, ast.ImportFrom):
            prefix = package[: len(package) - node.level + 1] if node.level else []
            module = ".".join([*prefix, *([node.module] if node.module else [])])
            if module == "recoup" or node.module is None:
                for alias in node.names:
                    check(f"{module}.{alias.name}", node)
            else:
                check(module, node)
        elif isinstance(node, ast.Call):
            call = node.func
            dynamic = (isinstance(call, ast.Name) and call.id in dynamic_names) or (
                isinstance(call, ast.Attribute)
                and call.attr in {"import_module", "__import__"}
                and isinstance(call.value, ast.Name)
                and call.value.id in importlib_names | builtins_names
            )
            if dynamic:
                name = (
                    node.args[0]
                    if node.args
                    else next((kw.value for kw in node.keywords if kw.arg == "name"), None)
                )
                if not isinstance(name, ast.Constant) or not isinstance(name.value, str):
                    errors.append(f"{node.lineno}: non-literal dynamic import")
                else:
                    module = name.value
                    if module.startswith("."):
                        relative_package = (
                            node.args[1]
                            if len(node.args) > 1
                            else next(
                                (kw.value for kw in node.keywords if kw.arg == "package"), None
                            )
                        )
                        if not isinstance(relative_package, ast.Constant) or not isinstance(
                            relative_package.value, str
                        ):
                            errors.append(f"{node.lineno}: non-literal dynamic import package")
                            continue
                        try:
                            module = resolve_name(module, relative_package.value)
                        except (ImportError, ValueError):
                            errors.append(f"{node.lineno}: invalid dynamic import package")
                            continue
                    check(module, node)
    return errors


def test_repository_import_dag():
    errors = []
    for folder in ["recoup", "tests"]:
        for path in (ROOT / folder).rglob("*.py"):
            errors.extend(
                f"{path.relative_to(ROOT)}:{error}"
                for error in violations(path.read_text(), path.relative_to(ROOT))
            )
    assert not errors, "\n".join(errors)


@pytest.mark.parametrize(
    ("path", "source"),
    [
        ("recoup/contracts/x.py", "import recoup.world"),
        ("recoup/engine/x.py", "def f():\n import recoup.world"),
        ("recoup/engine/x.py", "if TYPE_CHECKING:\n from recoup.world import SqliteWorld"),
        ("recoup/engine/x.py", "from ..world import store"),
        ("recoup/engine/x.py", "from recoup import world"),
        ("recoup/engine/x.py", "import importlib as il\nil.import_module('recoup.world')"),
        ("recoup/engine/x.py", "from importlib import import_module as load\nload('recoup.world')"),
        ("recoup/engine/x.py", "__import__('recoup.world')"),
        ("recoup/engine/x.py", "import builtins as b\nb.__import__('recoup.world')"),
        ("recoup/engine/x.py", "import importlib\nimportlib.import_module('.world', 'recoup')"),
        (
            "recoup/engine/x.py",
            "import importlib\nimportlib.import_module('.world', package=package)",
        ),
        ("recoup/engine/x.py", "import importlib\nimportlib.import_module(module_name)"),
        ("recoup/engine/x.py", "__import__(name='recoup.' + area)"),
        ("recoup/app.py", "import recoup.engine.factory"),
        ("recoup/app.py", "def build():\n import recoup.engine.rules"),
        ("recoup/app.py", "def build():\n from recoup.engine import factory"),
        ("tests/contracts/test_x.py", "import recoup.app"),
        ("tests/engine/test_x.py", "from recoup.world import store"),
        ("tests/ui/test_x.py", "import recoup.engine"),
        ("tests/bench/test_x.py", "import recoup.world"),
    ],
)
def test_guard_rejects_forbidden_edges(path, source):
    assert violations(source, Path(path))


@pytest.mark.parametrize(
    ("path", "source"),
    [
        ("recoup/contracts/x.py", "from .models import Citation"),
        (
            "recoup/contracts/x.py",
            "import importlib\nimportlib.import_module('.models', package='recoup.contracts')",
        ),
        ("recoup/world/x.py", "from recoup.contracts.models import Money"),
        ("recoup/engine/x.py", "from .rules import run_rules"),
        ("recoup/app.py", "def build():\n from recoup.engine.factory import build_engine"),
        (
            "recoup/app.py",
            "def build():\n import importlib\n importlib.import_module('recoup.engine.factory')",
        ),
        ("recoup/cli.py", "from recoup.app import build"),
        ("tests/contracts/test_x.py", "from recoup.contracts import models"),
        ("tests/world/test_x.py", "import recoup.world"),
        ("tests/app/test_x.py", "import recoup.cli"),
        ("tests/cli/test_x.py", "import recoup.app"),
        ("tests/engine/test_x.py", "from recoup.app import build"),
        ("tests/ui/test_x.py", "import recoup.ui"),
        ("tests/bench/test_x.py", "import recoup.bench"),
    ],
)
def test_guard_allows_normative_edges(path, source):
    assert violations(source, Path(path)) == []
