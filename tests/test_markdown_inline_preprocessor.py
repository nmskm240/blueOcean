import base64

import pytest

nbformat = pytest.importorskip("nbformat")
nbconvert = pytest.importorskip("nbconvert")
MarkdownExporter = nbconvert.MarkdownExporter

from blueOcean.jupyter.preprocessor import MarkdownInlineFigurePreprocessor


def _build_notebook_with_image() -> nbformat.NotebookNode:
    nb = nbformat.v4.new_notebook()
    image_bytes = b"fake-image-bytes"
    output = nbformat.v4.new_output(
        output_type="display_data",
        data={"image/png": base64.b64encode(image_bytes).decode("ascii")},
    )
    nb.cells.append(nbformat.v4.new_code_cell(source="print('hello')", outputs=[output]))
    return nb


def test_preprocessor_inlines_images_in_markdown_export():
    exporter = MarkdownExporter()
    exporter.register_preprocessor(MarkdownInlineFigurePreprocessor, enabled=True)

    nb = _build_notebook_with_image()
    body, resources = exporter.from_notebook_node(nb)

    assert "data:image/png;base64," in body
    # No files should remain because the preprocessor removes them from resources
    assert resources.get("outputs") == {}
