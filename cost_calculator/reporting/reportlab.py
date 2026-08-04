"""ReportLab document for one saved part-cost calculation."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


PAGE_SIZE = landscape(letter)
NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#2563A6")
LIGHT_BLUE = colors.HexColor("#EAF2F8")
LIGHT_GRAY = colors.HexColor("#F3F5F7")
MID_GRAY = colors.HexColor("#C8D0D8")
DARK_GRAY = colors.HexColor("#374151")
WHITE = colors.white


class RepeatingHeaderTable(Table):
    """Keep header styling when ReportLab recursively splits a long table."""

    def split(self, avail_width, avail_height):
        fragments = super().split(avail_width, avail_height)
        for fragment in fragments:
            if getattr(fragment, "repeatRows", 0):
                fragment.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("LINEBELOW", (0, 0), (-1, 0), 0.75, NAVY),
                        ]
                    )
                )
        return fragments


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _text(value: object, default: str = "-") -> str:
    if _is_missing(value):
        return default
    rendered = str(value).strip()
    return rendered or default


def _decimal(value: object) -> Decimal:
    if _is_missing(value):
        return Decimal("0")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")
    return result if result.is_finite() else Decimal("0")


def _number(value: object, places: int = 2) -> str:
    number = _decimal(value)
    if number == number.to_integral():
        return f"{number:,.0f}"
    rendered = f"{number:,.{places}f}"
    return rendered.rstrip("0").rstrip(".")


def _money(value: object, places: int = 2) -> str:
    return f"${_decimal(value):,.{places}f}"


def _date(value: object) -> str:
    if _is_missing(value):
        return "-"
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.strftime("%Y-%m-%d %H:%M" if isinstance(value, datetime) else "%Y-%m-%d")
    return _text(value)


def _bool_label(value: object) -> str:
    if _is_missing(value):
        return "No"
    return "Yes" if bool(value) else "No"


def _paragraph(value: object, style: ParagraphStyle, default: str = "-") -> Paragraph:
    return Paragraph(escape(_text(value, default)), style)


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=19,
            leading=22,
            textColor=NAVY,
            alignment=TA_LEFT,
            spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=DARK_GRAY,
        ),
        "section": ParagraphStyle(
            "SectionHeading",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=NAVY,
            spaceBefore=8,
            spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=DARK_GRAY,
        ),
        "body_right": ParagraphStyle(
            "BodyRight",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=DARK_GRAY,
            alignment=TA_RIGHT,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7,
            leading=8.5,
            textColor=DARK_GRAY,
        ),
        "small_right": ParagraphStyle(
            "SmallRight",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7,
            leading=8.5,
            textColor=DARK_GRAY,
            alignment=TA_RIGHT,
        ),
        "metric_label": ParagraphStyle(
            "MetricLabel",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=DARK_GRAY,
        ),
        "metric_value": ParagraphStyle(
            "MetricValue",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=17,
            textColor=BLUE,
            alignment=TA_RIGHT,
        ),
        "notes": ParagraphStyle(
            "Notes",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=DARK_GRAY,
            backColor=LIGHT_GRAY,
            borderColor=MID_GRAY,
            borderWidth=0.5,
            borderPadding=7,
        ),
    }


def _base_table_style(*, header: bool = True) -> TableStyle:
    commands: list[tuple] = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("TEXTCOLOR", (0, 0), (-1, -1), DARK_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, -1), (-1, -1), 0.35, MID_GRAY),
        ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [WHITE, LIGHT_GRAY]),
    ]
    if header:
        commands.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.75, NAVY),
            ]
        )
    return TableStyle(commands)


def _metadata_table(row: pd.Series, styles: dict[str, ParagraphStyle]) -> Table:
    labels = ["Part", "Revision", "Quantity", "Costed", "Costed by", "Current"]
    values = [
        _text(row.get("ucpPartID")),
        _text(row.get("ucpPartRevision"), "(none)"),
        _number(row.get("ucpCostQuantity"), 3),
        _date(row.get("ucpDateCosted")),
        _text(row.get("ucpCostedBy")),
        _bool_label(row.get("ucpIsCurrent")),
    ]
    cells = []
    for label, value in zip(labels, values):
        cells.append(
            [
                Paragraph(escape(label), styles["metric_label"]),
                _paragraph(value, styles["body"]),
            ]
        )
    table = Table(cells, colWidths=[0.68 * inch, 2.55 * inch] * 3)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GRAY),
                ("BOX", (0, 0), (-1, -1), 0.5, MID_GRAY),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#DDE3E8")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _cost_summary(row: pd.Series, styles: dict[str, ParagraphStyle]) -> list:
    categories = [
        ("Materials", "ucpMaterialsRawCost", "ucpMaterialsMarkedUpCost"),
        ("Machine time", "ucpMachineTimeRawCost", "ucpMachineTimeMarkedUpCost"),
        ("Labor", "ucpLaborRawCost", "ucpLaborMarkedUpCost"),
        ("External operations", "ucpExternalOperationsRawCost", "ucpExternalOperationsMarkedUpCost"),
        ("Additional", "ucpAdditionalRawCost", "ucpAdditionalMarkedUpCost"),
        ("Total", "ucpTotalRawCost", "ucpTotalMarkedUpCost"),
    ]
    summary = [["Cost category", "Raw", "Marked up"]]
    for label, raw_key, marked_key in categories:
        summary.append([label, _money(row.get(raw_key)), _money(row.get(marked_key))])

    summary_table = Table(summary, colWidths=[2.35 * inch, 1.25 * inch, 1.25 * inch], repeatRows=1)
    summary_table.setStyle(_base_table_style())
    summary_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("BACKGROUND", (0, -1), (-1, -1), LIGHT_BLUE),
                ("LINEABOVE", (0, -1), (-1, -1), 0.75, BLUE),
            ]
        )
    )

    metrics = Table(
        [
            [Paragraph("Unit raw cost", styles["metric_label"]), Paragraph(_money(row.get("ucpUnitRawCost"), 4), styles["metric_value"])],
            [Paragraph("Unit marked-up cost", styles["metric_label"]), Paragraph(_money(row.get("ucpUnitMarkedUpCost"), 4), styles["metric_value"])],
            [Paragraph("Retail unit price", styles["metric_label"]), Paragraph(_money(row.get("ucpRetailUnitPrice"), 4) if not _is_missing(row.get("ucpRetailUnitPrice")) else "-", styles["metric_value"])],
        ],
        colWidths=[1.65 * inch, 2.35 * inch],
    )
    metrics.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BLUE),
                ("BOX", (0, 0), (-1, -1), 0.75, BLUE),
                ("LINEBELOW", (0, 0), (-1, -2), 0.35, colors.HexColor("#B7CCE0")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    combined = Table([[summary_table, metrics]], colWidths=[5.15 * inch, 4.15 * inch])
    combined.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return [Paragraph("Cost summary", styles["section"]), combined]


def _materials_table(rows: pd.DataFrame, styles: dict[str, ParagraphStyle]) -> Table:
    if rows.empty:
        empty = Table([["No material lines were saved for this costing run."]], colWidths=[9.3 * inch])
        empty.setStyle(_base_table_style(header=False))
        return empty

    data: list[list[object]] = [[
        "Material", "Description", "Qty/assembly", "Total qty", "Source", "Unit cost", "Raw", "Marked up"
    ]]
    for _, row in rows.iterrows():
        data.append(
            [
                _paragraph(row.get("ucmMaterialID"), styles["small"]),
                _paragraph(row.get("ucmMaterialDescription"), styles["small"]),
                Paragraph(_number(row.get("ucmQtyPerAssembly"), 4), styles["small_right"]),
                Paragraph(_number(row.get("ucmTotalQuantityRequired"), 4), styles["small_right"]),
                _paragraph(row.get("ucmCostSource"), styles["small"]),
                Paragraph(_money(row.get("ucmUnitCost"), 4), styles["small_right"]),
                Paragraph(_money(row.get("ucmRawCost")), styles["small_right"]),
                Paragraph(_money(row.get("ucmMarkedUpCost")), styles["small_right"]),
            ]
        )
    table = RepeatingHeaderTable(
        data,
        colWidths=[1.0 * inch, 2.2 * inch, 0.85 * inch, 0.85 * inch, 1.0 * inch, 1.05 * inch, 1.05 * inch, 1.05 * inch],
        repeatRows=1,
        splitByRow=1,
    )
    table.setStyle(_base_table_style())
    table.setStyle(TableStyle([("ALIGN", (2, 1), (3, -1), "RIGHT"), ("ALIGN", (5, 1), (-1, -1), "RIGHT")]))
    return table


def _operations_table(rows: pd.DataFrame, styles: dict[str, ParagraphStyle]) -> Table:
    if rows.empty:
        empty = Table([["No operation lines were saved for this costing run."]], colWidths=[9.3 * inch])
        empty.setStyle(_base_table_style(header=False))
        return empty

    data: list[list[object]] = [[
        "Seq", "Work center", "Operation", "Description", "Setup hrs", "Cycle hrs", "External", "Raw", "Marked up"
    ]]
    for _, row in rows.iterrows():
        data.append(
            [
                _text(row.get("ucoPartOperationLineID")),
                _paragraph(row.get("ucoWorkCenterID"), styles["small"]),
                _paragraph(row.get("ucoOperationID"), styles["small"]),
                _paragraph(row.get("ucoOperationDescription"), styles["small"]),
                Paragraph(_number(row.get("ucoSetupTimeHours"), 4), styles["small_right"]),
                Paragraph(_number(row.get("ucoCycleTimeHours"), 4), styles["small_right"]),
                _bool_label(row.get("ucoExternalJob")),
                Paragraph(_money(row.get("ucoLineRawCost")), styles["small_right"]),
                Paragraph(_money(row.get("ucoLineMarkedUpCost")), styles["small_right"]),
            ]
        )
    table = RepeatingHeaderTable(
        data,
        colWidths=[0.42 * inch, 0.9 * inch, 0.8 * inch, 2.25 * inch, 0.7 * inch, 0.7 * inch, 0.65 * inch, 1.0 * inch, 1.0 * inch],
        repeatRows=1,
        splitByRow=1,
    )
    table.setStyle(_base_table_style())
    table.setStyle(TableStyle([("ALIGN", (0, 1), (0, -1), "RIGHT"), ("ALIGN", (4, 1), (5, -1), "RIGHT"), ("ALIGN", (7, 1), (-1, -1), "RIGHT")]))
    return table


def _page_decorations(canvas, doc, *, part_id: str, part_cost_id: str) -> None:
    canvas.saveState()
    width, _height = PAGE_SIZE
    canvas.setTitle(f"Part Cost Report - {part_id}")
    canvas.setAuthor("Product Cost Calculator")
    canvas.setStrokeColor(MID_GRAY)
    canvas.setLineWidth(0.4)
    canvas.line(doc.leftMargin, 0.48 * inch, width - doc.rightMargin, 0.48 * inch)
    canvas.setFillColor(DARK_GRAY)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(doc.leftMargin, 0.29 * inch, f"Part {part_id} - Costing run {part_cost_id}")
    canvas.drawRightString(width - doc.rightMargin, 0.29 * inch, f"Page {doc.page}")
    canvas.restoreState()


def render_part_cost_document(
    part_cost: pd.DataFrame,
    operation_lines: pd.DataFrame,
    material_lines: pd.DataFrame,
) -> bytes:
    """Return a complete, paginated PDF for a saved costing run."""
    if part_cost.empty:
        raise ValueError("A saved part cost is required to render the report")

    row = part_cost.iloc[0]
    part_id = _text(row.get("ucpPartID"), "part")
    part_cost_id = _text(row.get("ucpPartCostID"), "unknown")
    styles = _styles()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=PAGE_SIZE,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.65 * inch,
        title=f"Part Cost Report - {part_id}",
        author="Product Cost Calculator",
        subject=f"Saved costing run {part_cost_id}",
    )

    description = _text(row.get("ucpPartDescription"), "No description")
    story = [
        Paragraph("Part Cost Report", styles["title"]),
        Paragraph(escape(description), styles["subtitle"]),
        Spacer(1, 0.12 * inch),
        _metadata_table(row, styles),
        Spacer(1, 0.04 * inch),
        *_cost_summary(row, styles),
        Paragraph("Materials", styles["section"]),
        _materials_table(material_lines, styles),
        Paragraph("Operations", styles["section"]),
        _operations_table(operation_lines, styles),
    ]

    notes = _text(row.get("ucpNotes"), "")
    if notes:
        story.extend(
            [
                Paragraph("Notes", styles["section"]),
                Paragraph(escape(notes).replace("\n", "<br/>"), styles["notes"]),
            ]
        )

    page_callback = lambda canvas, current_doc: _page_decorations(
        canvas,
        current_doc,
        part_id=part_id,
        part_cost_id=part_cost_id,
    )
    doc.build(story, onFirstPage=page_callback, onLaterPages=page_callback)
    result = buffer.getvalue()
    if not result.startswith(b"%PDF-"):
        raise RuntimeError("ReportLab returned an invalid PDF")
    return result
