"""Immutable semantic-version value object.

Used for the benchmark version and the ontology version. Compatibility follows
the governance rule that MINOR changes are additive and backward compatible: an
available version *satisfies* a required version when they share a MAJOR and the
available version is at least the required version.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from synthaudit_bench.errors import VersionError

__all__ = ["Version"]

_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


@dataclass(frozen=True, slots=True, order=True)
class Version:
    """A ``MAJOR.MINOR.PATCH`` semantic version.

    Instances are immutable and ordered by (major, minor, patch). Construct from
    a string with :meth:`parse`.
    """

    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, text: str) -> Version:
        """Parse a ``MAJOR.MINOR.PATCH`` string.

        Raises:
            VersionError: if ``text`` is not a valid semantic-version triple.
        """
        match = _SEMVER.match(text)
        if match is None:
            raise VersionError(f"not a MAJOR.MINOR.PATCH version: {text!r}")
        return cls(int(match[1]), int(match[2]), int(match[3]))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def satisfies(self, required: Version) -> bool:
        """Return whether this available version satisfies ``required``.

        True when both share a MAJOR version and this version is at least
        ``required`` (the additive-minor compatibility rule).
        """
        return self.major == required.major and self >= required
