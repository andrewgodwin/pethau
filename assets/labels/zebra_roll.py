from django.conf import settings

from assets.models import Asset

from .zpl import ZplLabelTemplate, zpl_escape


def asset_url(asset: Asset) -> str:
    """
    The absolute URL of an asset's page, for encoding into a QR code.
    """
    return f"{settings.SITE_URL}{asset.urls.view}"


class Zebra3x1(ZplLabelTemplate):
    """
    Placeholder ZPL template for a 3" x 1" roll label at 203dpi.

    Deliberately minimal - a Code 128 with the tag underneath - so it can be replaced
    wholesale with a hand-tuned printer template.
    """

    slug = "zebra-3x1"
    name = 'Zebra 3" x 1" roll label (ZPL, 203dpi)'
    description = "Placeholder ZPL for a direct-thermal roll printer."

    dpi = 203
    width_inches = 3.0
    height_inches = 1.0

    def label_zpl(self, asset: Asset) -> str:
        tag = zpl_escape(asset.tag)
        return "\n".join(
            [
                "^CI28",
                f"^FO24,16^BY2,3,90^BCN,90,N,N,N^FD{tag}^FS",
                f"^FO24,120^A0N,42,42^FD{tag}^FS",
            ]
        )
