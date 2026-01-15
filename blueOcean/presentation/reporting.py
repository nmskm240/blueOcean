from __future__ import annotations

import base64
import io
from dataclasses import dataclass

import matplotlib.pyplot as plt
import pandas as pd
import quantstats as qs

from blueOcean.application.dto import TimeReturnPoint


@dataclass(frozen=True)
class ReportData:
    summary: dict[str, str]
    equity_image: str
    drawdown_image: str


def build_report(time_returns: list[TimeReturnPoint]) -> ReportData | None:
    returns = _build_returns(time_returns)
    if returns is None or returns.empty:
        return None

    report = _build_report_stats(returns)
    summary = {
        "total_return": _format_value(report.get("total_return"), True),
        "cagr": _format_value(report.get("cagr"), True),
        "sharpe": _format_value(report.get("sharpe"), False),
        "sortino": _format_value(report.get("sortino"), False),
        "volatility": _format_value(report.get("volatility"), True),
        "max_drawdown": _format_value(report.get("max_drawdown"), True),
        "win_rate": _format_value(report.get("win_rate"), True),
    }
    equity = (1 + returns).cumprod()
    drawdown = equity / equity.cummax() - 1
    return ReportData(
        summary=summary,
        equity_image=_build_line_chart(equity.index, equity.values, "Equity Curve"),
        drawdown_image=_build_line_chart(
            drawdown.index, drawdown.values, "Drawdown"
        ),
    )


def _build_returns(time_returns: list[TimeReturnPoint]) -> pd.Series | None:
    if not time_returns:
        return None
    return pd.Series(
        [point.value for point in time_returns],
        index=pd.to_datetime([point.timestamp for point in time_returns]),
        dtype=float,
    ).sort_index()


def _build_report_stats(returns: pd.Series) -> dict[str, float | None]:
    return {
        "total_return": _safe_stat(qs.stats.comp, returns),
        "cagr": _safe_stat(qs.stats.cagr, returns),
        "sharpe": _safe_stat(qs.stats.sharpe, returns),
        "sortino": _safe_stat(qs.stats.sortino, returns),
        "volatility": _safe_stat(qs.stats.volatility, returns),
        "max_drawdown": _safe_stat(qs.stats.max_drawdown, returns),
        "win_rate": _safe_stat(qs.stats.win_rate, returns),
    }


def _safe_stat(fn, *args, **kwargs) -> float | None:
    try:
        value = fn(*args, **kwargs)
    except Exception:
        return None
    if value is None:
        return None
    return float(value)


def _format_value(value: float | None, as_percent: bool) -> str:
    if value is None:
        return "-"
    return f"{value:.2%}" if as_percent else f"{value:.3f}"


def _build_line_chart(x, y, title: str) -> str:
    fig, ax = plt.subplots(figsize=(8, 2.6))
    ax.plot(x, y, linewidth=1.4)
    ax.set_title(title)
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=120)
    plt.close(fig)
    buffer.seek(0)
    encoded = base64.b64encode(buffer.read()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
