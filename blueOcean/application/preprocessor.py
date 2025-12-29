"""Custom nbconvert preprocessors for the blueOcean project."""
from __future__ import annotations

import base64
import html
import re
from html.parser import HTMLParser
from typing import Dict, Tuple

from nbconvert.preprocessors import Preprocessor
from nbformat import NotebookNode
from traitlets import Bool, List


class MarkdownInlineFigurePreprocessor(Preprocessor):
    """Inline extracted image outputs in Markdown exports.
    When nbconvert converts notebooks to Markdown it extracts binary outputs to
    the ``resources['outputs']`` dictionary and Markdown references the files by
    their generated names (for example ``figure_1.png``).  This preprocessor
    rewrites those references into ``data:`` URIs so the exported Markdown keeps
    the images embedded as Base64 instead of relying on external files.
    Only image MIME types listed in :attr:`inline_mimetypes` are processed.  By
    default PNG, JPEG, GIF and SVG outputs are handled.  The behaviour can be
    configured via the regular nbconvert configuration system.
    """

    inline_mimetypes = List(
        ["image/png", "image/jpeg", "image/gif", "image/svg+xml"],
        help="Image MIME types that should be embedded as Base64 in Markdown.",
    ).tag(config=True)

    remove_extracted_files = Bool(
        True,
        help=(
            "Remove processed files from resources['outputs'] so nbconvert "
            "does not try to write them to disk."
        ),
    ).tag(config=True)

    def preprocess(self, nb: NotebookNode, resources: Dict) -> Tuple[NotebookNode, Dict]:
        outputs = resources.get("outputs")
        if not outputs:
            return nb, resources

        for cell in nb.cells:
            if cell.get("cell_type") != "code":
                continue

            for output in cell.get("outputs", []):
                data = output.get("data")
                if not isinstance(data, dict):
                    continue

                metadata = output.setdefault("metadata", {})
                filenames = metadata.get("filenames")
                if not isinstance(filenames, dict):
                    continue

                for mimetype in list(data.keys()):
                    if mimetype not in self.inline_mimetypes:
                        continue

                    filename = filenames.get(mimetype)
                    if not filename:
                        continue

                    binary = outputs.get(filename)
                    if binary is None:
                        continue

                    data_uri = self._build_data_uri(binary, mimetype)
                    output['data']['text/markdown'] = f"![image]({data_uri})"

                    if self.remove_extracted_files:
                        outputs.pop(filename, None)

        return nb, resources

    @staticmethod
    def _build_data_uri(binary: bytes | str, mimetype: str) -> str:
        """Create a ``data:`` URI from raw binary data."""
        if isinstance(binary, str):
            try:
                raw_bytes = base64.b64decode(binary)
            except Exception:
                raw_bytes = binary.encode("utf-8")
        else:
            raw_bytes = binary

        encoded = base64.b64encode(raw_bytes).decode("ascii")
        return f"data:{mimetype};base64,{encoded}"


_TABLE_RE = re.compile(r"<table\b[^>]*>.*?</table>", re.IGNORECASE | re.DOTALL)
_STYLE_RE = re.compile(r"<style\b[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL)
_DIV_RE = re.compile(r"</?div\b[^>]*>", re.IGNORECASE)


class _HtmlTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[tuple[str, bool]]] = []
        self._current_row: list[tuple[str, bool]] = []
        self._current_cell: list[str] = []
        self._in_table = False
        self._in_cell = False
        self._cell_is_header = False

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "table":
            self._in_table = True
        if not self._in_table:
            return
        if tag == "tr":
            self._current_row = []
        elif tag in {"th", "td"}:
            self._in_cell = True
            self._cell_is_header = tag == "th"
            self._current_cell = []

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self._in_table:
            return
        if tag in {"th", "td"}:
            self._in_cell = False
            text = html.unescape("".join(self._current_cell)).strip()
            self._current_row.append((text, self._cell_is_header))
        elif tag == "tr":
            if self._current_row:
                self.rows.append(self._current_row)
            self._current_row = []
        elif tag == "table":
            self._in_table = False


def _table_to_markdown(table_html: str) -> str | None:
    parser = _HtmlTableParser()
    try:
        parser.feed(table_html)
    except Exception:
        return None

    rows = parser.rows
    if not rows:
        return None

    header_index = next(
        (idx for idx, row in enumerate(rows) if any(cell[1] for cell in row)),
        None,
    )
    if header_index is None:
        header_index = 0

    header_row = [cell[0] for cell in rows[header_index]]
    body_rows = [
        [cell[0] for cell in row]
        for idx, row in enumerate(rows)
        if idx != header_index
    ]

    column_count = max(len(header_row), *(len(row) for row in body_rows), 1)

    def _pad(row: list[str]) -> list[str]:
        return row + [""] * (column_count - len(row))

    def _escape(text: str) -> str:
        return text.replace("|", "\\|").replace("\n", "<br>")

    header_row = [_escape(value) for value in _pad(header_row)]
    body_rows = [[_escape(value) for value in _pad(row)] for row in body_rows]

    lines = [
        "| " + " | ".join(header_row) + " |",
        "| " + " | ".join(["---"] * column_count) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in body_rows)
    return "\n".join(lines)


def _replace_html_tables(content: str) -> str:
    if "<table" not in content.lower():
        return content

    cleaned = _STYLE_RE.sub("", content)
    cleaned = _DIV_RE.sub("", cleaned)

    def _replace(match: re.Match) -> str:
        table_html = match.group(0)
        markdown_table = _table_to_markdown(table_html)
        return markdown_table if markdown_table is not None else table_html

    return _TABLE_RE.sub(_replace, cleaned)


class MarkdownHtmlTablePreprocessor(Preprocessor):
    """Convert HTML tables in Markdown exports to Markdown tables."""

    convert_markdown_cells = Bool(
        True,
        help="Convert HTML tables inside markdown cells to Markdown tables.",
    ).tag(config=True)
    convert_output_html = Bool(
        True,
        help="Convert HTML tables in code cell outputs to Markdown tables.",
    ).tag(config=True)

    def preprocess(self, nb: NotebookNode, resources: Dict) -> Tuple[NotebookNode, Dict]:
        for cell in nb.cells:
            if self.convert_markdown_cells and cell.get("cell_type") == "markdown":
                source = cell.get("source", "")
                if isinstance(source, list):
                    source = "".join(source)
                cell["source"] = _replace_html_tables(source)

            if self.convert_output_html and cell.get("cell_type") == "code":
                for output in cell.get("outputs", []):
                    data = output.get("data")
                    if not isinstance(data, dict):
                        continue
                    html_text = data.get("text/html")
                    if not html_text:
                        continue
                    if isinstance(html_text, list):
                        html_text = "".join(html_text)
                    markdown_text = _replace_html_tables(html_text)
                    if markdown_text != html_text:
                        data["text/markdown"] = markdown_text
                        data["text/html"] = markdown_text

        return nb, resources
