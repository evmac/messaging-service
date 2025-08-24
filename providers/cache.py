from collections import OrderedDict
from collections.abc import KeysView, ValuesView
from typing import Any


class LRUCache:
    def __init__(self, *, max_size: int):
        self.cache: OrderedDict[str, Any] = OrderedDict()
        self.max_size = max_size

    def __setitem__(self, key: str, value: Any) -> None:
        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)
        else:
            # Add new item
            self.cache[key] = value
            # If we've exceeded max size, remove oldest
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)  # Remove first (oldest) item

    def __getitem__(self, key: str) -> Any:
        if key not in self.cache:
            raise KeyError(key)
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        return self.cache[key]

    def __contains__(self, key: str) -> bool:
        return key in self.cache

    def keys(self) -> KeysView[str]:
        return self.cache.keys()

    def values(self) -> ValuesView[Any]:
        return self.cache.values()
