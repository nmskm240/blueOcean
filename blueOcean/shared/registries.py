import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator, Type


@dataclass
class StrategyPageData:
    cls: Type
    notes: list[tuple[str, str | None]]
    source: str
    params: list[tuple[str, object]]


class _StrategyRegistryMeta(type):
    def __iter__(cls) -> Iterator[tuple[str, Type]]:
        return iter(cls._name_to_cls.items())


class StrategyRegistry(metaclass=_StrategyRegistryMeta):
    _name_to_cls: dict[str, Type] = {}
    _cls_to_name: dict[Type, str] = {}
    _name_to_params: dict[str, list[tuple[str, object]]] = {}
    _cls_to_params: dict[Type, list[tuple[str, object]]] = {}
    _name_to_page_data: dict[str, StrategyPageData] = {}
    _cls_to_page_data: dict[Type, StrategyPageData] = {}

    @classmethod
    def register(cls, name: str | None = None) -> Callable[[Type], Type]:
        def decorator(strategy_cls: Type) -> Type:
            resolved_name = name or strategy_cls.__name__
            if resolved_name in cls._name_to_cls:
                raise RuntimeError(f"Already registered: {resolved_name}")

            if strategy_cls in cls._cls_to_name:
                raise RuntimeError(f"Aready registered: {strategy_cls}")

            cls._name_to_cls[resolved_name] = strategy_cls
            cls._cls_to_name[strategy_cls] = resolved_name
            params = cls._extract_params(strategy_cls)
            cls._name_to_params[resolved_name] = params
            cls._cls_to_params[strategy_cls] = params
            if strategy_cls in cls._cls_to_page_data:
                page_data = cls._cls_to_page_data[strategy_cls]
                updated = StrategyPageData(
                    cls=strategy_cls,
                    notes=page_data.notes,
                    source=page_data.source,
                    params=params,
                )
                cls._cls_to_page_data[strategy_cls] = updated
                cls._name_to_page_data[resolved_name] = updated
            return strategy_cls

        return decorator

    @classmethod
    def register_page(
        cls, note_paths: list[tuple[str, str]] | None = None
    ) -> Callable[[Type], Type]:
        def decorator(strategy_cls: Type) -> Type:
            notes: list[tuple[str, str | None]] = []
            for title, path in note_paths or []:
                p = Path(path)
                content = p.read_text("utf-8") if p.exists() else None
                notes.append((title, content))

            try:
                source = inspect.getsource(strategy_cls)
            except OSError:
                source = ""

            params = cls._extract_params(strategy_cls)
            page_data = StrategyPageData(
                cls=strategy_cls, notes=notes, source=source, params=params
            )
            cls._cls_to_page_data[strategy_cls] = page_data
            name = cls._cls_to_name.get(strategy_cls)
            if name:
                cls._name_to_page_data[name] = page_data
            return strategy_cls

        return decorator

    @classmethod
    def resolve(cls, name: str) -> Type:
        try:
            return cls._name_to_cls[name]
        except KeyError:
            raise RuntimeError(f"Strategy not registered: {name}")

    @classmethod
    def name_of(cls, strategy_cls: Type) -> str:
        try:
            return cls._cls_to_name[strategy_cls]
        except KeyError:
            raise RuntimeError(f"Strategy class not registered: {strategy_cls}")

    @classmethod
    def params_of(cls, strategy: str | Type) -> list[tuple[str, object]]:
        if isinstance(strategy, str):
            try:
                return cls._name_to_params[strategy]
            except KeyError:
                raise RuntimeError(f"Strategy not registered: {strategy}")
        try:
            return cls._cls_to_params[strategy]
        except KeyError:
            raise RuntimeError(f"Strategy class not registered: {strategy}")

    @staticmethod
    def _extract_params(strategy_cls: Type) -> list[tuple[str, object]]:
        params = getattr(strategy_cls, "params", None)
        if params is None:
            return []
        if hasattr(params, "_getkeys"):
            return [(key, getattr(params, key)) for key in params._getkeys()]
        if isinstance(params, (list, tuple)):
            try:
                return [(name, value) for name, value in params]
            except ValueError:
                return []
        return []

    @classmethod
    def page_data_of(cls, strategy: str | Type) -> StrategyPageData | None:
        if isinstance(strategy, str):
            return cls._name_to_page_data.get(strategy)
        return cls._cls_to_page_data.get(strategy)

    @classmethod
    def iter_page_data(cls) -> Iterator[StrategyPageData]:
        return iter(cls._cls_to_page_data.values())
