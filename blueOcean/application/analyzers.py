from pathlib import Path
import backtrader as bt


class StreamingAnalyzer(bt.Analyzer):
    params = dict(
        analyzers=None,
        path=None,
    )

    def start(self):
        self.file = open(self.p.path.joinPath("metrics.csv"), "a", buffering=1)
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
