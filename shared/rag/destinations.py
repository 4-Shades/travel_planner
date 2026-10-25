"""The destination file, data/rag/destinations.txt: one destination per line, then its aliases.

    # Comments and blank lines are ignored.
    New York City | NYC
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Destination:
    name: str
    aliases: tuple[str, ...] = ()


def load_destinations(path):
    destinations = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            name, *aliases = [part.strip() for part in line.split("|")]
            destinations.append(Destination(name, tuple(alias for alias in aliases if alias)))
    return destinations


def alias_map(destinations):
    """Map every name and alias to its destination's name. Matching is exact (TP-SRS-083)."""
    return {alias: d.name for d in destinations for alias in (d.name, *d.aliases)}
