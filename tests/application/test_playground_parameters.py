import pytest

nbformat = pytest.importorskip("nbformat")

from blueOcean.application.playground import NotebookParameterInspector


def test_inspector_parses_parameters_from_tagged_cell(tmp_path, monkeypatch):
    nb = nbformat.v4.new_notebook()
    cell = nbformat.v4.new_code_cell(
        "alpha = 1\nbeta = 'x'\ngamma = None",
        metadata={"tags": ["parameters"]},
    )
    nb.cells.append(cell)
    notebook_path = tmp_path / "sample.ipynb"
    nbformat.write(nb, notebook_path)

    inspector = NotebookParameterInspector()
    monkeypatch.setattr(inspector, "_inspect_with_papermill", lambda _: None)

    params = inspector.inspect(notebook_path)

    param_map = {param.name: param for param in params}
    assert param_map["alpha"].default == 1
    assert param_map["beta"].default == "x"
    assert param_map["gamma"].default is None
