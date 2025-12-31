from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import ast

from nbconvert import MarkdownExporter
from nbformat import read
from papermill import execute_notebook, inspect_notebook

from blueOcean.application.dto import NotebookParameterInfo
from blueOcean.application.preprocessor import (
    MarkdownHtmlTablePreprocessor,
    MarkdownInlineFigurePreprocessor,
)


@dataclass(frozen=True)
class NotebookExecutionResult:
    markdown: str
    output_path: str


class NotebookExecutionService:
    def execute(
        self,
        notebook_path: Path,
        output_path: Path,
        parameters: dict[str, Any],
    ) -> NotebookExecutionResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        execute_notebook(
            str(notebook_path),
            str(output_path),
            parameters=parameters,
        )

        with output_path.open("r", encoding="utf-8") as fh:
            notebook = read(fh, as_version=4)

        exporter = MarkdownExporter()
        exporter.register_preprocessor(MarkdownHtmlTablePreprocessor, enabled=True)
        exporter.register_preprocessor(MarkdownInlineFigurePreprocessor, enabled=True)
        body, _ = exporter.from_notebook_node(notebook)

        return NotebookExecutionResult(markdown=body, output_path=str(output_path))


class NotebookParameterInspector:
    def inspect(self, notebook_path: Path) -> list[NotebookParameterInfo]:
        inspected = self._inspect_with_papermill(notebook_path)
        if inspected is not None:
            return inspected
        return self._inspect_with_json(notebook_path)

    def _inspect_with_papermill(
        self, notebook_path: Path
    ) -> list[NotebookParameterInfo] | None:
        try:
            raw = inspect_notebook(str(notebook_path))
        except Exception:
            return None

        parameters: list[NotebookParameterInfo] = []
        if isinstance(raw, dict):
            raw_parameters = raw.get("parameters")
            if isinstance(raw_parameters, dict):
                for name, info in raw_parameters.items():
                    if isinstance(info, dict):
                        default = info.get("default")
                        inferred = info.get("type")
                    else:
                        default = info
                        inferred = None
                    parameters.append(
                        NotebookParameterInfo(
                            name=str(name),
                            default=default,
                            inferred_type=str(inferred) if inferred else None,
                        )
                    )
        elif isinstance(raw, list):
            for item in raw:
                name = getattr(item, "name", None) or item.get("name")
                default = getattr(item, "default", None) or item.get("default")
                inferred = getattr(item, "inferred_type", None) or item.get(
                    "inferred_type"
                )
                if name is None:
                    continue
                parameters.append(
                    NotebookParameterInfo(
                        name=str(name),
                        default=default,
                        inferred_type=str(inferred) if inferred else None,
                    )
                )

        return parameters or None

    def _inspect_with_json(self, notebook_path: Path) -> list[NotebookParameterInfo]:
        with notebook_path.open("r", encoding="utf-8") as fh:
            notebook = read(fh, as_version=4)

        parameters: dict[str, Any] = {}
        for cell in notebook.cells:
            if cell.get("cell_type") != "code":
                continue
            tags = cell.get("metadata", {}).get("tags", [])
            if "parameters" not in tags:
                continue
            source = cell.get("source", "")
            if isinstance(source, list):
                source = "".join(source)
            parameters.update(self._parse_assignment_parameters(source))

        return [
            NotebookParameterInfo(
                name=name,
                default=value,
                inferred_type=type(value).__name__ if value is not None else None,
            )
            for name, value in parameters.items()
        ]

    @staticmethod
    def _parse_assignment_parameters(source: str) -> dict[str, Any]:
        parsed: dict[str, Any] = {}
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return parsed

        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if not isinstance(target, ast.Name):
                    continue
                name = target.id
                try:
                    value = ast.literal_eval(node.value)
                except Exception:
                    value = None
                parsed[name] = value
        return parsed
