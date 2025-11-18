"""Custom nbconvert preprocessors for the blueOcean project."""
from __future__ import annotations

import base64
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
                    filenames[mimetype] = data_uri

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
