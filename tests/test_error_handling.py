from fastapi import FastAPI
from fastapi.testclient import TestClient

from blueOcean.app import register_exception_handlers


def make_broken_app():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/broken-page")
    def broken_page():
        raise RuntimeError("sensitive failure detail")

    @app.get("/api/broken")
    def broken_api():
        raise RuntimeError("sensitive failure detail")

    return app


def test_unexpected_page_error_uses_generic_dialog():
    response = TestClient(make_broken_app(), raise_server_exceptions=False).get("/broken-page")

    assert response.status_code == 500
    assert 'class="modal" open' in response.text
    assert "予想外のエラーが発生しました" in response.text
    assert "sensitive failure detail" not in response.text


def test_unexpected_api_error_uses_generic_json():
    response = TestClient(make_broken_app(), raise_server_exceptions=False).get("/api/broken")

    assert response.status_code == 500
    assert response.json() == {"detail": "予想外のエラーが発生しました"}
    assert "sensitive failure detail" not in response.text
