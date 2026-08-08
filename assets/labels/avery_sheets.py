from django.conf import settings
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas

from assets.models import Asset

from .pdf import SheetLabelTemplate, draw_code128, draw_qr, truncate


def asset_url(asset: Asset) -> str:
    """
    The absolute URL of an asset's page, for encoding into a QR code.
    """
    return f"{settings.SITE_URL}{asset.urls.view}"


class Avery5160(SheetLabelTemplate):
    """
    Avery 5160: 30 labels of 2.625" x 1" per US Letter sheet, 3 across by 10 down.

    Full-width Code 128 across the top, then the tag, name and model as text with a QR
    code of the asset's URL in the bottom-right corner.
    """

    slug = "avery-5160"
    name = 'Avery 5160 - 2.625" x 1", 30 per US Letter sheet'
    description = "Address-label sheet. Barcode, text and QR."

    page_size = letter
    columns = 3
    rows = 10
    label_width = 2.625 * inch
    label_height = 1.0 * inch
    margin_left = 0.23 * inch
    margin_top = 0.55 * inch
    pitch_x = 2.75 * inch
    pitch_y = 1.0 * inch

    padding = 5
    barcode_height = 26
    qr_size = 33

    def draw_label(
        self,
        canvas: Canvas,
        asset: Asset,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> None:
        pad = self.padding
        draw_code128(
            canvas,
            asset.tag,
            x + pad,
            y + height - pad - self.barcode_height,
            width - pad * 2,
            self.barcode_height,
        )
        draw_qr(
            canvas,
            asset_url(asset),
            x + width - pad - self.qr_size,
            y + pad + 2,
            self.qr_size,
        )

        text_width = width - pad * 3 - self.qr_size
        lines = [(asset.tag, "Helvetica-Bold", 9.5)]
        if asset.name:
            lines.append((asset.name, "Helvetica", 7.5))
        lines.append((asset.model.display_name(), "Helvetica", 7.5))

        baseline = y + height - pad - self.barcode_height - 10
        for text, font, size in lines:
            canvas.setFont(font, size)
            canvas.drawString(
                x + pad, baseline, truncate(canvas, text, font, size, text_width)
            )
            baseline -= size + 2.5


class Avery6467(SheetLabelTemplate):
    """
    Avery 6467: 80 labels of 1.75" x 0.5" per US Letter sheet, 4 across by 20 down.

    Code 128 with name and tag only
    """

    slug = "avery-6467"
    name = 'Avery 6467 - 1.75" x 0.5", 80 per US Letter sheet'
    description = "Small tag labels. Barcode, name and tag only."

    page_size = letter
    columns = 4
    rows = 20
    label_width = 1.75 * inch
    label_height = 0.5 * inch
    margin_left = 0.5 * inch
    margin_top = 0.5 * inch
    pitch_x = 2.0 * inch
    pitch_y = 0.5 * inch

    padding = 2
    barcode_height = 20

    def draw_label(
        self,
        canvas: Canvas,
        asset: Asset,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> None:
        pad = self.padding
        draw_code128(
            canvas,
            asset.tag,
            x + pad,
            y + height - pad - self.barcode_height,
            width - pad * 2,
            self.barcode_height,
        )
        if asset.name:
            canvas.setFont("Helvetica-Bold", 7.5)
            canvas.drawString(x + pad, y + pad + 1.5, asset.tag)
            canvas.setFont("Helvetica", 7.5)
            canvas.setFont("Helvetica", 7.5)
            name_width = canvas.stringWidth(asset.name, "Helvetica", 7.5)
            canvas.drawString(
                x + width - (pad * 2) - name_width, y + pad + 1.5, asset.name
            )
        else:
            canvas.setFont("Helvetica-Bold", 7.5)
            canvas.drawCentredString(x + width / 2, y + (pad * 2) + 1.5, asset.tag)
