import argparse

from dataclasses import dataclass
from typing import Callable

@dataclass
class Tool:
    name: str
    description: str
    add_argparser: Callable[[argparse._SubParsersAction], None]
    main: Callable[..., bool]

    def __call__(self, **kwargs) -> bool: # type: ignore[no-untyped-def]
        return self.main(**kwargs)
