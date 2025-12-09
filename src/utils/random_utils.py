import random
from typing import List, Any

class RandomState:
    def __init__(self, seed: int):
        self._rng = random.Random(seed)

    def shuffle(self, seq: List[Any]) -> None:
        self._rng.shuffle(seq)

    def choice(self, seq: List[Any]) -> Any:
        return self._rng.choice(seq)

    def random(self) -> float:
        return self._rng.random()