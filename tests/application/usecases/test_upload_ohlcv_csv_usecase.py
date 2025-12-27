import pandas as pd

from blueOcean.application.services import OhlcvCsvImporter
from blueOcean.application.usecases import UploadOhlcvCsvUsecase
from blueOcean.infra.database.repositories import OhlcvRepository


def test_upload_ohlcv_csv_usecase_saves_parquet(tmp_path):
    csv_path = tmp_path / "ohlcv.csv"
    df = pd.DataFrame(
        [
            {
                "open": 100,
                "close": 110,
                "datetime": "2024-01-10 00:00:00",
                "high": 120,
                "low": 90,
            },
            {
                "open": 200,
                "close": 210,
                "datetime": "2024-02-05T00:00:00Z",
                "high": 220,
                "low": 180,
            },
        ]
    )
    df.to_csv(csv_path, index=False)

    repository = OhlcvRepository(base_path=str(tmp_path))
    importer = OhlcvCsvImporter()
    usecase = UploadOhlcvCsvUsecase(importer=importer, ohlcv_repository=repository)

    usecase.execute("binance", "BTC/USDT", str(csv_path))

    jan_path = tmp_path / "binance" / "BTC_USDT" / "2024-01.parquet"
    feb_path = tmp_path / "binance" / "BTC_USDT" / "2024-02.parquet"

    assert jan_path.exists()
    assert feb_path.exists()

    jan_df = pd.read_parquet(jan_path)
    feb_df = pd.read_parquet(feb_path)

    assert jan_df.loc[0, "volume"] == 0.0
    assert feb_df.loc[0, "volume"] == 0.0
    assert jan_df["time"].dt.tz is None
    assert feb_df["time"].dt.tz is None
