from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Tuple, TypeVar, get_args, get_origin
import inspect

import pandas as pd

from .backtest import (
    BacktestResult,
    create_sample_ohlcv,
    prepare_ohlcv_dataframe,
    run_backtest,
)


StrategyClass = TypeVar("StrategyClass", bound=type)


@dataclass
class StrategyParameter:
    name: str
    annotation: object | None
    default: object | None
    has_default: bool


@dataclass
class StrategyPage:
    title: str
    description: str | None
    strategy_cls: type
    extra_renderer: Callable[[type], None] | None = None

    def render(self) -> None:
        """Render the page using Streamlit."""
        import streamlit as st  # imported lazily to keep tests light

        st.title(self.title)
        if self.description:
            st.write(self.description)

        doc = inspect.getdoc(self.strategy_cls)
        if doc:
            st.info(doc)

        params = self.get_parameters()
        st.subheader("利用可能なパラメータ")
        if params:
            for param in params.values():
                annotation = (
                    param.annotation.__name__
                    if isinstance(param.annotation, type)
                    else str(param.annotation)
                    if param.annotation is not None
                    else "未指定"
                )
                if param.has_default:
                    st.markdown(
                        f"- `{param.name}` (型: {annotation}) — デフォルト: {param.default}"
                    )
                else:
                    st.markdown(f"- `{param.name}` (型: {annotation}) — 必須")
        else:
            st.write("初期化パラメータはありません。")

        if self.extra_renderer:
            self.extra_renderer(self.strategy_cls)

        self._render_backtest_section(st, params)

    def get_parameters(self) -> Dict[str, StrategyParameter]:
        signature = inspect.signature(self.strategy_cls.__init__)
        params: Dict[str, StrategyParameter] = {}
        for name, parameter in signature.parameters.items():
            if name == "self" or parameter.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                continue
            has_default = parameter.default is not inspect._empty
            default = parameter.default if has_default else None
            annotation = (
                None if parameter.annotation is inspect._empty else parameter.annotation
            )
            params[name] = StrategyParameter(
                name=name,
                annotation=annotation,
                default=default,
                has_default=has_default,
            )
        return params

    def _render_backtest_section(
        self,
        st_module,
        params: Dict[str, StrategyParameter],
    ) -> None:
        st = st_module

        st.subheader("バックテストを実行")
        st.caption(
            "CSVは `datetime,open,high,low,close,volume` の列を含むフォーマットに対応しています。"
        )

        form_key = f"{self.strategy_cls.__name__}_backtest_form"
        data_option = "サンプルデータ"
        uploaded_file = None
        raw_param_inputs: Dict[str, str] = {}

        with st.form(form_key):
            data_option = st.radio(
                "価格データのソース",
                options=["サンプルデータ", "CSVファイルをアップロード"],
                horizontal=True,
                key=f"{form_key}_data_source",
            )

            if data_option == "CSVファイルをアップロード":
                uploaded_file = st.file_uploader(
                    "OHLCV形式のCSVファイル",
                    type=["csv"],
                    key=f"{form_key}_uploader",
                )

            st.markdown("### Strategyパラメータ")
            for param in params.values():
                default_value = "" if not param.has_default else str(param.default)
                placeholder = _parameter_placeholder(param)
                raw_param_inputs[param.name] = st.text_input(
                    label=f"{param.name}",
                    value=default_value,
                    key=f"{form_key}_{param.name}",
                    placeholder=placeholder,
                )

            submitted = st.form_submit_button("バックテストを実行")

        if not submitted:
            return

        data_frame: pd.DataFrame | None = None

        if data_option == "CSVファイルをアップロード":
            if uploaded_file is None:
                st.error("CSVファイルが選択されていません。")
                return
            try:
                data_frame = _load_csv_to_dataframe(uploaded_file)
            except Exception as exc:  # pragma: no cover - streamlit runtime only
                st.error(f"CSVの読み込みに失敗しました: {exc}")
                return
        else:
            data_frame = create_sample_ohlcv()

        parsed_params, errors = _parse_parameter_inputs(params, raw_param_inputs)
        if errors:
            for error in errors:
                st.error(error)
            return

        try:
            result = run_backtest(self.strategy_cls, data_frame, **parsed_params)
        except Exception as exc:  # pragma: no cover - streamlit runtime only
            st.error(f"バックテストの実行に失敗しました: {exc}")
            return

        _render_backtest_result(st, result)


_strategy_pages: List[StrategyPage] = []


def strategy_page(
    title: str | None = None,
    description: str | None = None,
    *,
    extra_renderer: Callable[[type], None] | None = None,
) -> Callable[[StrategyClass], StrategyClass]:
    """Decorator used to register a strategy class as a Streamlit page."""

    def decorator(cls: StrategyClass) -> StrategyClass:
        page = StrategyPage(
            title=title or cls.__name__,
            description=description,
            strategy_cls=cls,
            extra_renderer=extra_renderer,
        )
        _strategy_pages.append(page)
        cls.streamlit_page = page  # type: ignore[attr-defined]
        return cls

    return decorator


def list_strategy_pages() -> Tuple[StrategyPage, ...]:
    return tuple(_strategy_pages)


def clear_strategy_pages() -> None:
    _strategy_pages.clear()


def _parameter_placeholder(param: StrategyParameter) -> str:
    annotation = param.annotation
    if isinstance(annotation, type):
        return f"型: {annotation.__name__}"
    if annotation is None:
        return "値を入力"
    return f"型: {annotation}"


def _parse_parameter_inputs(
    params: Dict[str, StrategyParameter], raw_inputs: Dict[str, str]
) -> Tuple[Dict[str, Any], List[str]]:
    parsed: Dict[str, Any] = {}
    errors: List[str] = []

    for name, param in params.items():
        raw_value = raw_inputs.get(name, "").strip()
        if not raw_value:
            if param.has_default:
                parsed[name] = param.default
            else:
                errors.append(f"{name} は必須です。")
            continue

        try:
            parsed[name] = _convert_parameter_value(raw_value, param)
        except ValueError as exc:
            errors.append(str(exc))

    return parsed, errors


def _convert_parameter_value(value: str, param: StrategyParameter) -> Any:
    annotation = _resolve_annotation(param.annotation)
    target_type = annotation if isinstance(annotation, type) else None

    if target_type is int:
        return int(value)
    if target_type is float:
        return float(value)
    if target_type is bool:
        lower = value.lower()
        if lower in {"true", "1", "yes", "y"}:
            return True
        if lower in {"false", "0", "no", "n"}:
            return False
        raise ValueError(f"{param.name} の値 '{value}' を真偽値に変換できません。")
    if target_type is str or target_type is None:
        return value

    # Fallback: return as string to keep flexibility
    return value


def _resolve_annotation(annotation: object | None) -> object | None:
    if annotation is None:
        return None
    origin = get_origin(annotation)
    if origin is None:
        return annotation
    if origin is list:
        return list
    args = [arg for arg in get_args(annotation) if arg is not type(None)]  # noqa: E721
    if len(args) == 1:
        return args[0]
    return annotation


def _load_csv_to_dataframe(uploaded_file) -> pd.DataFrame:
    df = pd.read_csv(uploaded_file)
    datetime_column = _detect_datetime_column(df.columns)
    if datetime_column is None:
        raise ValueError("datetime列が見つかりませんでした。")

    df[datetime_column] = pd.to_datetime(df[datetime_column])
    df = df.set_index(datetime_column)
    return prepare_ohlcv_dataframe(df)


def _detect_datetime_column(columns: List[str]) -> str | None:
    candidates = {"datetime", "date", "time", "timestamp"}
    lowered = {col.lower(): col for col in columns}
    for candidate in candidates:
        if candidate in lowered:
            return lowered[candidate]
    return None


def _render_backtest_result(st_module, result: BacktestResult) -> None:
    st = st_module
    st.success(f"バックテスト完了: 最終資産額 {result.final_value:,.2f}")

    metrics_columns = st.columns(3)
    trade_stats = result.analyzers.get("trade", {}) or {}
    total_trades = trade_stats.get("total", {}).get("total", 0)
    won_trades = trade_stats.get("won", {}).get("total", 0)
    lost_trades = trade_stats.get("lost", {}).get("total", 0)
    sharpe = result.analyzers.get("sharpe", {}).get("sharperatio")

    metrics_columns[0].metric("取引回数", f"{total_trades}")
    metrics_columns[1].metric("勝ちトレード", f"{won_trades}")
    metrics_columns[2].metric("負けトレード", f"{lost_trades}")

    if sharpe is not None:
        st.metric("シャープレシオ", f"{sharpe:.2f}")

    try:
        figure = result.plot()
    except RuntimeError as exc:  # pragma: no cover - plot errors are user facing only
        st.warning(f"グラフの描画に失敗しました: {exc}")
    else:
        st.pyplot(figure)
