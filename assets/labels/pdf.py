from io import BytesIO

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.code128 import Code128
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen.canvas import Canvas

from assets.models import Asset

from .base import LabelTemplate

# Quiet zone either side of a Code 128 symbol, in modules (the spec asks for at least 10)
QUIET_MODULES = 10


def draw_code128(
    canvas: Canvas, value: str, x: float, y: float, width: float, height: float
) -> None:
    """
    Draws a Code 128 barcode scaled to exactly fill `width`, including quiet zones.

    Symbol width is linear in bar width, so one measure-then-rescale pass is enough.
    """
    measured = Code128(
        value, barWidth=1, barHeight=height, humanReadable=False, quiet=False
    ).width
    bar_width = width / (measured + QUIET_MODULES * 2)
    barcode = Code128(
        value, barWidth=bar_width, barHeight=height, humanReadable=False, quiet=False
    )
    barcode.drawOn(canvas, x + QUIET_MODULES * bar_width, y)


def draw_qr(canvas: Canvas, data: str, x: float, y: float, size: float) -> None:
    """
    Draws a QR code as a `size` x `size` square with its bottom-left corner at (x, y).
    """
    widget = QrCodeWidget(data, barLevel="M")
    left, bottom, right, top = widget.getBounds()
    drawing = Drawing(
        size, size, transform=[size / (right - left), 0, 0, size / (top - bottom), 0, 0]
    )
    drawing.add(widget)
    renderPDF.draw(drawing, canvas, x, y)


def truncate(canvas: Canvas, text: str, font: str, size: float, width: float) -> str:
    """
    Shortens `text` with an ellipsis until it fits within `width` at the given font.
    """
    if canvas.stringWidth(text, font, size) <= width:
        return text
    while text and canvas.stringWidth(text + "…", font, size) > width:
        text = text[:-1]
    return text + "…"


class SheetLabelTemplate(LabelTemplate):
    """
    Base class for templates that lay labels out in a grid on a paper sheet.

    Subclasses set the geometry and implement `draw_label`, which draws a single label
    into a box whose bottom-left corner is at (x, y).
    """

    page_size = letter
    columns: int
    rows: int
    label_width: float
    label_height: float
    margin_left: float
    margin_top: float
    pitch_x: float
    pitch_y: float

    supports_offset = True

    @property
    def per_page(self) -> int:
        return self.columns * self.rows

    def cell_origin(self, index: int) -> tuple[float, float]:
        """
        The bottom-left corner of the `index`th label on a page, filling left-to-right
        then top-to-bottom.
        """
        _, page_height = self.page_size
        row, column = divmod(index, self.columns)
        x = self.margin_left + column * self.pitch_x
        y = (
            page_height
            - self.margin_top
            - (row + 1) * self.pitch_y
            + (self.pitch_y - self.label_height)
        )
        return x, y

    def render(self, assets: list[Asset], *, offset: int = 0) -> bytes:
        buffer = BytesIO()
        canvas = Canvas(buffer, pagesize=self.page_size)
        canvas.setTitle("Labels")
        # Blank out the labels already used on a part-used sheet
        cells = [None] * max(offset, 0) + list(assets)
        for index, asset in enumerate(cells):
            if index and index % self.per_page == 0:
                canvas.showPage()
            if asset is None:
                continue
            x, y = self.cell_origin(index % self.per_page)
            self.draw_label(canvas, asset, x, y, self.label_width, self.label_height)
        canvas.showPage()
        canvas.save()
        return buffer.getvalue()

    def draw_label(
        self,
        canvas: Canvas,
        asset: Asset,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> None:
        raise NotImplementedError()
