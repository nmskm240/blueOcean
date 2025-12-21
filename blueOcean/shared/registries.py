from typing import Callable, Iterator, Type


class _StrategyRegistryMeta(type):
    def __iter__(cls) -> Iterator[tuple[str, Type]]:
        return iter(cls._name_to_cls.items())


class StrategyRegistry(metaclass=_StrategyRegistryMeta):
    _name_to_cls: dict[str, Type] = {}
    _cls_to_name: dict[Type, str] = {}
    _name_to_params: dict[str, list[tuple[str, object]]] = {}
    _cls_to_params: dict[Type, list[tuple[str, object]]] = {}

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
