import ast
import re
from pathlib import Path

from recoup.contracts import bundle, interfaces, models, money, oracle, tools


def test_normative_model_fields_and_port_signatures():
    design = (
        Path(__file__).resolve().parents[2] / "docs/design/02-technical-design.md"
    ).read_text()
    for section, module in [
        ("3.1", money),
        ("3.2", models),
        ("3.3", bundle),
        ("3.4", tools),
        ("3.5", interfaces),
        ("8.1", oracle),
    ]:
        section_text = design.split(f"### {section} ", 1)[1].split("\n### ", 1)[0]
        blocks = re.findall(r"```python\n(.*?)```", section_text, re.S)
        actual_ast = ast.parse(Path(module.__file__).read_text())
        actual_classes = {
            node.name: node for node in actual_ast.body if isinstance(node, ast.ClassDef)
        }
        for node in ast.parse("\n".join(blocks)).body:
            if not isinstance(node, ast.ClassDef):
                continue
            assert node.name in actual_classes
            actual = actual_classes[node.name]
            expected_fields = {
                field.target.id: ast.unparse(field.annotation)
                for field in node.body
                if isinstance(field, ast.AnnAssign)
            }
            actual_fields = {
                field.target.id: ast.unparse(field.annotation)
                for field in actual.body
                if isinstance(field, ast.AnnAssign)
            }
            assert actual_fields == expected_fields, node.name
            cls = getattr(module, node.name)
            if hasattr(cls, "model_fields"):
                assert set(cls.model_fields) == set(expected_fields)
                for field in node.body:
                    if isinstance(field, ast.AnnAssign):
                        assert cls.model_fields[field.target.id].is_required() == (
                            field.value is None
                        )
            for method in node.body:
                if isinstance(method, ast.FunctionDef):
                    implementation = next(
                        m
                        for m in actual.body
                        if isinstance(m, ast.FunctionDef) and m.name == method.name
                    )
                    assert ast.dump(implementation.args) == ast.dump(method.args)
                    assert ast.dump(implementation.returns) == ast.dump(method.returns)
