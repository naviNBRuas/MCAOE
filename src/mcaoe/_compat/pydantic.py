from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Union, get_args, get_origin, get_type_hints
from uuid import UUID

try:  # pragma: no cover - preferred path when dependency is installed
    from pydantic import BaseModel as BaseModel  # type: ignore
    from pydantic import Field as Field  # type: ignore
except Exception:  # pragma: no cover - fallback used in minimal environments
    @dataclass(slots=True)
    class _FieldSpec:
        default: Any = ...
        default_factory: Callable[[], Any] | None = None

    def Field(*, default: Any = ..., default_factory: Callable[[], Any] | None = None, **_: Any) -> Any:
        return _FieldSpec(default=default, default_factory=default_factory)

    class BaseModel:
        def __init__(self, **data: Any) -> None:
            cls = self.__class__
            hints = get_type_hints(cls)
            for name in _model_fields(cls):
                if name in data:
                    value = data[name]
                else:
                    value = _default_for(cls, name)
                coerced = _coerce_value(hints.get(name, Any), value)
                object.__setattr__(self, name, coerced)

        def model_dump(self, mode: str | None = None) -> dict[str, Any]:
            return {
                name: _dump_value(getattr(self, name), mode=mode)
                for name in _model_fields(self.__class__)
            }

        @classmethod
        def model_validate(cls, data: Any) -> "BaseModel":
            if isinstance(data, cls):
                return data
            if not isinstance(data, dict):
                raise TypeError(f"Expected mapping for {cls.__name__}, got {type(data)!r}")
            return cls(**data)

        def __repr__(self) -> str:
            values = ", ".join(f"{name}={getattr(self, name)!r}" for name in _model_fields(self.__class__))
            return f"{self.__class__.__name__}({values})"

    def _model_fields(cls: type) -> list[str]:
        hints = get_type_hints(cls)
        return [name for name in hints if not name.startswith("_")]

    def _default_for(cls: type, field_name: str) -> Any:
        value = getattr(cls, field_name, ...)
        if isinstance(value, _FieldSpec):
            if value.default_factory is not None:
                return value.default_factory()
            if value.default is not ...:
                return value.default
            return None
        if value is not ...:
            return value
        return None

    def _coerce_value(expected_type: Any, value: Any) -> Any:
        if value is None:
            return None

        origin = get_origin(expected_type)
        args = get_args(expected_type)

        if origin is list:
            item_type = args[0] if args else Any
            return [_coerce_value(item_type, item) for item in value]

        if origin is dict:
            value_type = args[1] if len(args) > 1 else Any
            return {key: _coerce_value(value_type, item) for key, item in value.items()}

        if origin in (Union,):
            non_none = [arg for arg in args if arg is not type(None)]
            if len(non_none) == 1:
                return _coerce_value(non_none[0], value)
            return value

        if isinstance(expected_type, type) and issubclass(expected_type, BaseModel):
            if isinstance(value, dict):
                return expected_type.model_validate(value)
            return value

        if isinstance(expected_type, type) and issubclass(expected_type, Enum):
            if isinstance(value, expected_type):
                return value
            return expected_type(value)

        if expected_type is UUID:
            return value if isinstance(value, UUID) else UUID(str(value))

        if expected_type is datetime:
            return value if isinstance(value, datetime) else datetime.fromisoformat(str(value))

        return value

    def _dump_value(value: Any, mode: str | None = None) -> Any:
        if isinstance(value, BaseModel):
            return value.model_dump(mode=mode)
        if isinstance(value, list):
            return [_dump_value(item, mode=mode) for item in value]
        if isinstance(value, dict):
            return {key: _dump_value(item, mode=mode) for key, item in value.items()}
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        return value
