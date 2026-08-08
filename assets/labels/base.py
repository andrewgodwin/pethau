from dataclasses import dataclass, field

from assets.models import Asset


@dataclass
class LabelItem:
    """
    A single asset and how many copies of its label to print.
    """

    asset: Asset
    quantity: int


@dataclass
class ParsedSpec:
    """
    The result of parsing a label spec string.

    `items` are the resolved assets in the order they were first mentioned, `notices` are
    non-fatal remarks (e.g. range members that don't exist), and `errors` are fatal - if
    any are present the spec must not be printed.
    """

    items: list[LabelItem] = field(default_factory=list)
    notices: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(item.quantity for item in self.items)

    @property
    def is_printable(self) -> bool:
        return not self.errors and bool(self.items)

    def assets(self) -> list[Asset]:
        """
        The items flattened out into one entry per physical label.
        """
        result = []
        for item in self.items:
            result.extend([item.asset] * item.quantity)
        return result


class LabelTemplate:
    """
    Base class for label templates.

    Subclasses declare their identity and implement `render`, which turns a flat list of
    assets (one entry per physical label) into the bytes of a printable document.
    """

    slug: str
    name: str
    format: str = "pdf"
    content_type: str = "application/pdf"
    extension: str = "pdf"
    supports_offset: bool = False
    description: str = ""

    def render(self, assets: list[Asset], *, offset: int = 0) -> bytes:
        raise NotImplementedError()
