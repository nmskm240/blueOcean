from pathlib import Path
import backtrader as bt


class StreamingAnalyzer(bt.Analyzer):
    params = dict(
        analyzers=None,
        path=None,
    )

    def start(self):
        metrics_path = Path(self.p.path) / "metrics.csv"
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        file_exists = metrics_path.exists()
        self.file = open(metrics_path, "a", buffering=1)
        if not file_exists or metrics_path.stat().st_size == 0:
            self.file.write("timestamp,analyzer,key,value\n")

    def next(self):
        ts = self.strategy.datas[0].datetime.datetime(0)

        for name, analyzer in self.strategy.analyzers.getitems():
            if self.p.analyzers and name not in self.p.analyzers:
                continue

            try:
                data = analyzer.get_analysis()
            except Exception:
                continue

            # TimeReturn は累積 dict を返すので、最新 1 件だけを書き込む
            if isinstance(analyzer, bt.analyzers.TimeReturn):
                if not data:
                    continue
                last_key, last_value = next(reversed(data.items()))
                self.file.write(f"{ts},{name},{last_key},{last_value}\n")
                continue

            self._flatten_and_write(ts, name, data)

    def _flatten_and_write(self, ts, analyzer_name, data, prefix=""):
        if isinstance(data, dict):
            for k, v in data.items():
                self._flatten_and_write(ts, analyzer_name, v, f"{prefix}{k}.")
        else:
            self.file.write(f"{ts},{analyzer_name},{prefix[:-1]},{data}\n")

    def stop(self):
        self.file.close()

    def __getstate__(self):
        state = self.__dict__.copy()
        state["file"] = None
        return state
    
