"""Fixed bank of memory slots (joint plan D3-a: "next free group").

The hippocampal model separates memories through its CA3 sequence groups,
which are fixed when the network is built. Each memory therefore takes one
slot, and slot s is the model's pattern index s: with ``--n-patterns N`` and
``--n-groups N`` pattern s is exactly CA3 group s. When every slot is taken,
``assign`` raises ``CapacityError``.

No storage of its own: the memory service replays ``remember`` in insertion
order when it reopens a database, so every memory gets back the same slot.
"""

from __future__ import annotations

from .base import CapacityError


class SlotBank:
    def __init__(self, n_slots: int) -> None:
        if n_slots < 1:
            raise ValueError("n_slots must be >= 1")
        self.n_slots = n_slots
        self._slot_of: dict[str, int] = {}
        self._memory_in: list[str | None] = [None] * n_slots

    def assign(self, memory_id: str) -> int:
        """Give memory_id the lowest free slot; the same id keeps its slot."""
        if memory_id in self._slot_of:
            return self._slot_of[memory_id]
        try:
            slot = self._memory_in.index(None)
        except ValueError:
            raise CapacityError(f"all {self.n_slots} slots are taken") from None
        self._slot_of[memory_id] = slot
        self._memory_in[slot] = memory_id
        return slot

    def slot_of(self, memory_id: str) -> int | None:
        return self._slot_of.get(memory_id)

    def memory_in(self, slot: int) -> str | None:
        """The memory a decoded slot points to (None for an empty slot)."""
        return self._memory_in[slot]

    def free(self) -> int:
        return self._memory_in.count(None)

    def clear(self) -> None:
        self._slot_of.clear()
        self._memory_in = [None] * self.n_slots
