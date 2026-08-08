from assets.models import Asset

from .base import LabelTemplate


def zpl_escape(value: str) -> str:
    """
    Strips the characters ZPL treats as control prefixes from field data.
    """
    return value.replace("^", "").replace("~", "")


class ZplLabelTemplate(LabelTemplate):
    """
    Base class for templates that emit ZPL II for a direct-thermal label printer.

    Subclasses implement `label_zpl`, which returns the body of a single label; `render`
    wraps each one in ^XA/^XZ and concatenates them.
    """

    format = "zpl"
    content_type = "text/plain; charset=utf-8"
    extension = "zpl"
    supports_offset = False

    dpi = 203
    width_inches: float
    height_inches: float

    @property
    def width_dots(self) -> int:
        return round(self.width_inches * self.dpi)

    @property
    def height_dots(self) -> int:
        return round(self.height_inches * self.dpi)

    def render(self, assets: list[Asset], *, offset: int = 0) -> bytes:
        labels = [
            f"^XA\n^PW{self.width_dots}\n^LL{self.height_dots}\n{self.label_zpl(asset)}\n^XZ"
            for asset in assets
        ]
        return ("\n".join(labels) + "\n").encode("utf-8")

    def label_zpl(self, asset: Asset) -> str:
        raise NotImplementedError()
