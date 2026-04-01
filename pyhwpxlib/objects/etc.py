"""Port of etc/UnparsedXMLFile.java."""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Optional


@dataclass
class UnparsedXMLFile:
    """Stores unparsed XML content by href."""

    href: Optional[str] = None
    xml: Optional[str] = None

    def clone(self) -> UnparsedXMLFile:
        return copy.deepcopy(self)

    def copy_from(self, from_obj: UnparsedXMLFile) -> None:
        self.href = from_obj.href
        self.xml = from_obj.xml
