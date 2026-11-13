"""D3-a slot bank: one memory per model pattern slot."""

import pytest

from llm.backends import CapacityError, SlotBank


def test_next_free_slot_and_capacity():
    bank = SlotBank(3)
    assert [bank.assign(m) for m in ("a", "b", "c")] == [0, 1, 2]
    assert bank.assign("b") == 1          # same memory keeps its slot
    assert bank.memory_in(2) == "c" and bank.free() == 0
    with pytest.raises(CapacityError):
        bank.assign("d")


def test_same_order_gives_same_slots():
    # the service replays remember() in insertion order on reopen
    ids = ["x", "y", "z"]
    one, two = SlotBank(5), SlotBank(5)
    assert [one.assign(i) for i in ids] == [two.assign(i) for i in ids]


def test_clear_and_bad_size():
    bank = SlotBank(2)
    bank.assign("a")
    bank.clear()
    assert bank.free() == 2 and bank.slot_of("a") is None
    with pytest.raises(ValueError):
        SlotBank(0)
