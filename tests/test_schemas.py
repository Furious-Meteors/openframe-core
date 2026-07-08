"""
tests/test_schemas.py
========================
Tests for openframe.core.schemas — the @contract marker (ADR-007).
"""
from __future__ import annotations

import pytest
from pydantic import BaseModel

from openframe.core.schemas import ContractMeta, contract, get_contract_meta


def test_contract_decorator_attaches_meta() -> None:
    @contract(name="item", version="1.0")
    class Item(BaseModel):
        id: str
        name: str

    assert Item.__contract__.name == "item"
    assert Item.__contract__.version == "1.0"


def test_contract_decorator_returns_class_unchanged() -> None:
    class RawItem(BaseModel):
        id: str
        name: str

    DecoratedItem = contract(name="item", version="1.0")(RawItem)

    assert DecoratedItem is RawItem
    instance = DecoratedItem(id="1", name="widget")
    assert isinstance(instance, RawItem)
    assert DecoratedItem.model_json_schema() == RawItem.model_json_schema()


def test_get_contract_meta_returns_meta_for_decorated_class() -> None:
    @contract(name="order", version="2.1")
    class Order(BaseModel):
        id: str

    meta = get_contract_meta(Order)
    assert meta is not None
    assert meta.name == "order"
    assert meta.version == "2.1"


def test_get_contract_meta_returns_none_for_undecorated_class() -> None:
    class PlainModel(BaseModel):
        id: str

    assert get_contract_meta(PlainModel) is None


def test_contract_decorator_works_on_nested_model() -> None:
    class Address(BaseModel):
        street: str
        city: str

    @contract(name="customer", version="1.0")
    class Customer(BaseModel):
        id: str
        address: Address

    instance = Customer(id="1", address=Address(street="Main St", city="Springfield"))
    assert instance.address.city == "Springfield"
    assert get_contract_meta(Customer).name == "customer"


def test_contract_meta_repr() -> None:
    assert repr(ContractMeta("item", "1.0")) == "ContractMeta(name='item', version='1.0')"


def test_contract_marker_does_not_affect_pydantic_validation() -> None:
    class PlainModel(BaseModel):
        id: str
        count: int

    @contract(name="counted", version="1.0")
    class DecoratedModel(BaseModel):
        id: str
        count: int

    plain = PlainModel(id="1", count=5)
    decorated = DecoratedModel(id="1", count=5)
    assert plain.model_dump() == decorated.model_dump()

    with pytest.raises(Exception):
        PlainModel(id="1", count="not-an-int")
    with pytest.raises(Exception):
        DecoratedModel(id="1", count="not-an-int")
