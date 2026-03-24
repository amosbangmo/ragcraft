from __future__ import annotations

from enum import Enum

from application.http.wire.json_wire import jsonify_value


class _E(Enum):
    X = 3


class _Box:
    value = "inner"


class _WithDict:
    def to_dict(self):
        return {"nested": 1}


def test_jsonify_tuple_and_enum_value() -> None:
    assert jsonify_value((1, "a")) == [1, "a"]
    assert jsonify_value(_E.X) == 3


def test_jsonify_box_with_value_attr() -> None:
    assert jsonify_value(_Box()) == "inner"


def test_jsonify_to_dict_object() -> None:
    assert jsonify_value(_WithDict()) == {"nested": 1}


def test_jsonify_fallback_str() -> None:
    out = jsonify_value(object())
    assert isinstance(out, str)
    assert out
