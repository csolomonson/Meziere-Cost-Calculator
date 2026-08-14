"""Portrait, monochrome costing documents organized around their readers."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
import math
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    CondPageBreak,
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


PAGE_SIZE = letter
PAGE_WIDTH, _PAGE_HEIGHT = PAGE_SIZE
CONTENT_WIDTH = 7.3 * inch
BLACK = colors.black
WHITE = colors.white


class ReportAudience:
    INTERNAL = "internal"
    CUSTOMER = "customer"


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


def _float(value: object) -> float:
    return float(_decimal(value))


def _number(value: object, places: int = 3) -> str:
    number = _decimal(value)
    if number == number.to_integral():
        return f"{number:,.0f}"
    return f"{number:,.{places}f}".rstrip("0").rstrip(".")


def _money(value: object, places: int = 2) -> str:
    return f"${_decimal(value):,.{places}f}"


def _factor(value: object) -> str:
    return f"{_decimal(value):,.3f}x"


def _date(value: object, *, include_time: bool = False) -> str:
    if _is_missing(value):
        return "-"
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.strftime("%Y-%m-%d %H:%M" if include_time else "%Y-%m-%d")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    return _text(value)


def _bool(value: object, default: bool = False) -> bool:
    if _is_missing(value):
        return default
    if isinstance(value, str):
        return value.strip().lower() not in {"", "0", "false", "no", "n"}
    return bool(value)


def _paragraph(value: object, style: ParagraphStyle, default: str = "-") -> Paragraph:
    return Paragraph(escape(_text(value, default)), style)


def _markup_paragraph(markup: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(markup, style)


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "eyebrow": ParagraphStyle(
            "Eyebrow",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
            textColor=BLACK,
            spaceAfter=3,
        ),
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=21,
            textColor=BLACK,
            alignment=TA_LEFT,
            spaceAfter=3,
        ),
        "customer_title": ParagraphStyle(
            "CustomerTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=21,
            leading=24,
            textColor=BLACK,
            alignment=TA_LEFT,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=BLACK,
            spaceAfter=5,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=BLACK,
            keepWithNext=True,
            spaceBefore=12,
            spaceAfter=3,
        ),
        "subsection": ParagraphStyle(
            "Subsection",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=BLACK,
            keepWithNext=True,
            spaceBefore=8,
            spaceAfter=2,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=BLACK,
            spaceAfter=3,
        ),
        "body_right": ParagraphStyle(
            "BodyRight",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=BLACK,
            alignment=TA_RIGHT,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
            textColor=BLACK,
        ),
        "small_right": ParagraphStyle(
            "SmallRight",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
            textColor=BLACK,
            alignment=TA_RIGHT,
        ),
        "label": ParagraphStyle(
            "Label",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
            textColor=BLACK,
        ),
        "value": ParagraphStyle(
            "Value",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=11,
            textColor=BLACK,
        ),
        "price": ParagraphStyle(
            "Price",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=19,
            textColor=BLACK,
            alignment=TA_RIGHT,
        ),
        "metric_inline": ParagraphStyle(
            "MetricInline",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7,
            leading=16,
            textColor=BLACK,
            alignment=TA_RIGHT,
        ),
        "center": ParagraphStyle(
            "Center",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=BLACK,
            alignment=TA_CENTER,
        ),
    }


def _rule(*, thickness: float = 0.55, space_before: float = 2, space_after: float = 5):
    return HRFlowable(
        width="100%",
        thickness=thickness,
        color=BLACK,
        spaceBefore=space_before,
        spaceAfter=space_after,
    )


def _plain_table(
    data: list[list[object]],
    widths: list[float],
    *,
    header: bool = False,
    repeat_rows: int = 0,
    right_columns: tuple[int, ...] = (),
    bold_last: bool = False,
    font_size: float = 7.2,
    padding: float = 3.5,
) -> Table:
    table = Table(data, colWidths=widths, repeatRows=repeat_rows, splitByRow=1)
    commands: list[tuple] = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("TEXTCOLOR", (0, 0), (-1, -1), BLACK),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), padding),
        ("RIGHTPADDING", (0, 0), (-1, -1), padding),
        ("TOPPADDING", (0, 0), (-1, -1), padding),
        ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
    ]
    if header:
        commands.extend(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.7, BLACK),
                ("BOTTOMPADDING", (0, 0), (-1, 0), padding + 1),
            ]
        )
    for column in right_columns:
        commands.append(("ALIGN", (column, 1 if header else 0), (column, -1), "RIGHT"))
    if bold_last and len(data) > 1:
        commands.extend(
            [
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("LINEABOVE", (0, -1), (-1, -1), 0.7, BLACK),
                ("LINEBELOW", (0, -1), (-1, -1), 0.7, BLACK),
            ]
        )
    table.setStyle(TableStyle(commands))
    return table


def _identity_table(row: pd.Series, styles: dict[str, ParagraphStyle], *, internal: bool) -> Table:
    values = [
        ("Part", _text(row.get("ucpPartID"))),
        ("Revision", _text(row.get("ucpPartRevision"), "None")),
        ("Description", _text(row.get("ucpPartDescription"), "No description")),
        ("Cost quantity", _number(row.get("ucpCostQuantity"))),
        ("Cost date", _date(row.get("ucpDateCosted"), include_time=internal)),
        ("Reference", f"Costing run {_text(row.get('ucpPartCostID'), 'unsaved')}"),
    ]
    if internal:
        values.extend(
            [
                ("Prepared by", _text(row.get("ucpCostedBy"))),
                ("Current saved cost", "Yes" if _bool(row.get("ucpIsCurrent")) else "No"),
            ]
        )
    cells: list[list[object]] = []
    for index in range(0, len(values), 2):
        left = values[index]
        right = values[index + 1]
        cells.append(
            [
                Paragraph(escape(left[0]), styles["label"]),
                Paragraph(escape(left[1]), styles["value"]),
                Paragraph(escape(right[0]), styles["label"]),
                Paragraph(escape(right[1]), styles["value"]),
            ]
        )
    return _plain_table(cells, [0.85 * inch, 2.7 * inch, 0.9 * inch, 2.85 * inch], padding=2.5)


SUMMARY_BUCKETS = [
    ("Materials", "ucpMaterialsRawCost", "ucpMaterialsMarkedUpCost"),
    ("Machine", "ucpMachineTimeRawCost", "ucpMachineTimeMarkedUpCost"),
    ("Labor", "ucpLaborRawCost", "ucpLaborMarkedUpCost"),
    ("Outside processing", "ucpExternalOperationsRawCost", "ucpExternalOperationsMarkedUpCost"),
    ("Additional", "ucpAdditionalRawCost", "ucpAdditionalMarkedUpCost"),
]


def _internal_conclusion(row: pd.Series, styles: dict[str, ParagraphStyle]) -> list[object]:
    quantity = _float(row.get("ucpCostQuantity"))
    raw_total = _float(row.get("ucpTotalRawCost"))
    sell_total = _float(row.get("ucpTotalMarkedUpCost"))
    raw_unit = raw_total / quantity if quantity else 0
    sell_unit = sell_total / quantity if quantity else 0
    metric_style = styles["metric_inline"]
    price_cells = [[
        Paragraph(
            f"<b>PRODUCTION QTY</b>&#160;&#160;<font size='14'><b>{escape(_number(quantity))}</b></font>",
            metric_style,
        ),
        Paragraph(
            f"<b>RAW COST/UNIT</b>&#160;&#160;<font size='14'><b>{escape(_money(raw_unit, 4))}</b></font>",
            metric_style,
        ),
        Paragraph(
            f"<b>CALCULATED PRICE/UNIT</b>&#160;&#160;<font size='14'><b>{escape(_money(sell_unit, 4))}</b></font>",
            metric_style,
        ),
    ]]
    price_table = _plain_table(
        price_cells,
        [1.65 * inch, 2.55 * inch, 3.1 * inch],
        right_columns=(0, 1, 2),
        padding=1.5,
    )

    data: list[list[object]] = [["Cost element", "Raw cost", "% raw", "Effective factor", "Calculated price", "Price/unit"]]
    for label, raw_key, sell_key in SUMMARY_BUCKETS:
        raw = _float(row.get(raw_key))
        sell = _float(row.get(sell_key))
        data.append(
            [
                label,
                _money(raw),
                f"{raw / raw_total:.1%}" if raw_total else "-",
                _factor(sell / raw) if raw else "-",
                _money(sell),
                _money(sell / quantity, 4) if quantity else "-",
            ]
        )
    data.append(
        [
            "Total",
            _money(raw_total),
            "100.0%" if raw_total else "-",
            _factor(sell_total / raw_total) if raw_total else "-",
            _money(sell_total),
            _money(sell_unit, 4),
        ]
    )
    summary = _plain_table(
        data,
        [1.45 * inch, 1.0 * inch, 0.65 * inch, 1.0 * inch, 1.1 * inch, 1.0 * inch],
        header=True,
        repeat_rows=1,
        right_columns=(1, 2, 3, 4, 5),
        bold_last=True,
    )
    retail = row.get("ucpRetailUnitPrice")
    retail_note = "No ERP retail price was saved with this costing run."
    if not _is_missing(retail):
        retail_note = (
            f"The ERP retail reference saved with this run was {_money(retail, 4)} per unit. "
            "It is shown as a comparison only and is not used in the cost build-up above."
        )
    return [
        Paragraph("Cost conclusion", styles["section"]),
        _rule(),
        price_table,
        Spacer(1, 0.04 * inch),
        summary,
        Spacer(1, 0.05 * inch),
        Paragraph(escape(retail_note), styles["small"]),
    ]


def _source_name(value: object) -> str:
    return {
        "purchase_order": "purchase order",
        "manufactured_current": "current manufactured-part cost",
        "manufactured_history": "historical manufactured-part cost",
        "manufactured_route": "ERP manufacturing estimate",
        "erp_estimate": "ERP estimated unit cost",
        "manual_override": "manual override",
        "Last PO": "purchase order",
    }.get(_text(value, "").strip(), _text(value, "unspecified source").replace("_", " "))


def _material_source_explanation(row: pd.Series) -> str:
    source = _text(row.get("ucmCostSource"), "").strip()
    unit_cost = _money(row.get("ucmUnitCost"), 4)
    if source in {"purchase_order", "Last PO"} or _bool(row.get("ucmIsPurchased")):
        po = _text(row.get("ucmLastPO"), "not recorded")
        po_date = _date(row.get("ucmLastPODate"))
        purchase_cost = row.get("ucmLastPOPurchaseUnitCost")
        if _is_missing(purchase_cost):
            purchase_cost = row.get("ucmPurchaseUnitCost")
        factor = _float(row.get("ucmLastPOConversionFactor")) or 1
        purchase_unit = _text(row.get("ucmLastPOPurchaseUnit"), "purchase unit")
        inventory_unit = _text(row.get("ucmLastPOInventoryUnit"), "inventory unit")
        return (
            f"Source: PO {po}, {po_date} | {_money(purchase_cost, 4)}/{purchase_unit} x "
            f"{_number(factor, 6)} conversion = {unit_cost}/{inventory_unit}."
        )
    if source in {"manufactured_current", "manufactured_history"}:
        run_value = row.get("ucmManufacturedPartCostID")
        run_id = "not recorded" if _is_missing(run_value) else _number(run_value)
        status = "current" if _bool(row.get("ucmManufacturedPartCostIsCurrent")) else "historical"
        return f"Source: manufactured cost run {run_id} ({status}) | {unit_cost}/unit; component cost buckets carried through below."
    if source == "manual_override":
        return f"Source: manual override | {unit_cost}/unit."
    if source == "manufactured_route":
        return f"Source: ERP manufacturing estimate | no saved component cost; {unit_cost}/unit used."
    return f"Source: {_source_name(source)} | {unit_cost}/unit."


MATERIAL_BUCKETS = [
    ("Material", "ucmMaterialsRawCost", "ucmMaterialsMarkedUpCost"),
    ("Machine inherited from component", "ucmMachineTimeRawCost", "ucmMachineTimeMarkedUpCost"),
    ("Labor inherited from component", "ucmLaborRawCost", "ucmLaborMarkedUpCost"),
    ("Outside processing inherited from component", "ucmExternalOperationsRawCost", "ucmExternalOperationsMarkedUpCost"),
    ("Additional inherited from component", "ucmAdditionalRawCost", "ucmAdditionalMarkedUpCost"),
]


def _backflushed_materials(rows: pd.DataFrame) -> pd.DataFrame:
    """Return only materials that participate in the saved product costing."""
    if rows.empty or "ucmBackflush" not in rows.columns:
        return rows.iloc[0:0]
    included = rows["ucmBackflush"].map(lambda value: _bool(value, default=False))
    return rows.loc[included]


def _summary_name(identifier: object, description: object, styles: dict[str, ParagraphStyle]) -> Paragraph:
    return Paragraph(
        f"<b>{escape(_text(identifier))}</b> - {escape(_text(description, 'No description'))}",
        styles["small"],
    )


def _internal_line_summary(
    materials: pd.DataFrame,
    operations: pd.DataFrame,
    styles: dict[str, ParagraphStyle],
) -> list[object]:
    flow: list[object] = [
        Paragraph("Costed line summary", styles["section"]),
        _rule(),
    ]

    flow.append(Paragraph(f"Materials ({len(materials)})", styles["subsection"]))
    if materials.empty:
        flow.append(Paragraph("No backflushed materials.", styles["small"]))
    else:
        material_rows: list[list[object]] = [["Material", "Qty/part", "Raw cost", "Calculated price"]]
        for _, row in materials.iterrows():
            material_rows.append(
                [
                    _summary_name(row.get("ucmMaterialID"), row.get("ucmMaterialDescription"), styles),
                    _number(row.get("ucmQtyPerAssembly")),
                    _money(row.get("ucmRawCost")),
                    _money(row.get("ucmMarkedUpCost")),
                ]
            )
        material_rows.append(
            ["Material lines", "", _money(_sum(materials, "ucmRawCost")), _money(_sum(materials, "ucmMarkedUpCost"))]
        )
        flow.append(
            _plain_table(
                material_rows,
                [4.05 * inch, 0.85 * inch, 1.1 * inch, 1.3 * inch],
                header=True,
                repeat_rows=1,
                right_columns=(1, 2, 3),
                bold_last=True,
                font_size=6.7,
                padding=2.3,
            )
        )

    if not operations.empty and len(materials) + len(operations) > 8:
        flow.extend(
            [
                PageBreak(),
                Paragraph("Costed line summary (continued)", styles["section"]),
                _rule(),
            ]
        )
    flow.append(Paragraph(f"Operations ({len(operations)})", styles["subsection"]))
    if operations.empty:
        flow.append(Paragraph("No saved operations.", styles["small"]))
    else:
        operation_rows: list[list[object]] = [["Operation", "Work center", "Raw cost", "Calculated price"]]
        for _, row in operations.iterrows():
            operation_rows.append(
                [
                    _summary_name(
                        f"{_text(row.get('ucoPartOperationLineID'))} / {_text(row.get('ucoOperationID'))}",
                        row.get("ucoOperationDescription"),
                        styles,
                    ),
                    _text(row.get("ucoWorkCenterID"), "-"),
                    _money(row.get("ucoLineRawCost")),
                    _money(row.get("ucoLineMarkedUpCost")),
                ]
            )
        operation_rows.append(
            ["Operation lines", "", _money(_sum(operations, "ucoLineRawCost")), _money(_sum(operations, "ucoLineMarkedUpCost"))]
        )
        flow.append(
            _plain_table(
                operation_rows,
                [4.05 * inch, 0.85 * inch, 1.1 * inch, 1.3 * inch],
                header=True,
                repeat_rows=1,
                right_columns=(2, 3),
                bold_last=True,
                font_size=6.7,
                padding=2.3,
            )
        )
    return flow


def _material_detail(
    index: int,
    row: pd.Series,
    styles: dict[str, ParagraphStyle],
    report_quantity: float,
) -> list[object]:
    material_id = _text(row.get("ucmMaterialID"), "Unidentified material")
    description = _text(row.get("ucmMaterialDescription"), "No description")
    per_assembly = _float(row.get("ucmQtyPerAssembly"))
    required = _float(row.get("ucmTotalQuantityRequired"))
    if not required:
        required = per_assembly * report_quantity
    waste = _float(row.get("ucmWasteQuantity"))
    quantity_costed = required + waste
    increment = _float(row.get("ucmMinimumPurchaseQty"))
    raw = _float(row.get("ucmRawCost"))
    priced = _float(row.get("ucmMarkedUpCost"))
    multiplier = _float(row.get("ucmMaterialMarkup")) or 1

    heading = f"{index}. {escape(material_id)} - {escape(description)}"
    quantity_rows = [
        ["Question", "Calculation", "Result"],
        ["Net quantity required", f"{_number(per_assembly)} per assembly x {_number(report_quantity)} assemblies", _number(required)],
        ["Purchase increment", "Saved minimum/increment used for rounding", _number(increment) if increment else "No rounding"],
        ["Quantity charged", f"Net required {_number(required)} + rounding/waste {_number(waste)}", _number(quantity_costed)],
    ]
    result_rows: list[list[object]] = [["Cost component", "Raw cost", "Factor", "Calculated price"]]
    for label, raw_key, priced_key in MATERIAL_BUCKETS:
        bucket_raw = _float(row.get(raw_key))
        bucket_priced = _float(row.get(priced_key))
        if bucket_raw or bucket_priced:
            result_rows.append([label, _money(bucket_raw), _factor(bucket_priced / bucket_raw) if bucket_raw else "-", _money(bucket_priced)])
    if len(result_rows) == 1:
        result_rows.append(["Material", _money(raw), _factor(multiplier), _money(priced)])
    result_rows.append(["Line contribution", _money(raw), _factor(priced / raw) if raw else _factor(multiplier), _money(priced)])

    formula = (
        f"Line cost: {_number(quantity_costed)} x {_money(row.get('ucmUnitCost'), 4)} = {_money(raw)} raw; "
        f"x {_factor(multiplier)} = {_money(priced)}."
    )
    return [
        CondPageBreak(3.3 * inch),
        KeepTogether([Paragraph(heading, styles["subsection"]), _rule(thickness=0.35, space_after=3)]),
        Paragraph(escape(_material_source_explanation(row)), styles["body"]),
        _plain_table(quantity_rows, [1.5 * inch, 4.55 * inch, 1.25 * inch], header=True, repeat_rows=1, right_columns=(2,)),
        KeepTogether(
            [
                Spacer(1, 0.03 * inch),
                Paragraph(escape(formula), styles["body"]),
                _plain_table(
                    result_rows,
                    [3.65 * inch, 1.15 * inch, 1.05 * inch, 1.45 * inch],
                    header=True,
                    repeat_rows=1,
                    right_columns=(1, 2, 3),
                    bold_last=True,
                ),
            ]
        ),
    ]


def _materials_section(rows: pd.DataFrame, styles: dict[str, ParagraphStyle], report_quantity: float) -> list[object]:
    flow: list[object] = [
        KeepTogether(
            [
                Paragraph("Material cost build-up", styles["section"]),
                _rule(),
                Paragraph(
                    "Backflushed materials only. Source, quantity extension, and cost contribution follow for each line.",
                    styles["body"],
                ),
            ]
        ),
    ]
    if rows.empty:
        flow.append(Paragraph("No material components were saved with this costing run.", styles["body"]))
        return flow
    for display_index, (_, row) in enumerate(rows.iterrows(), start=1):
        flow.extend(_material_detail(display_index, row, styles, report_quantity))
    return flow


def _operation_quantities(row: pd.Series, report_quantity: float) -> tuple[float, float, int, int]:
    per_assembly = _float(row.get("ucoQuantityPerAssembly")) or 1
    operation_quantity = report_quantity * per_assembly
    batch_size = _float(row.get("ucoBatchSize"))
    batches = math.ceil(operation_quantity / batch_size) if batch_size > 0 and operation_quantity > 0 else 0
    resets = max(batches - 1, 0)
    return per_assembly, operation_quantity, batches, resets


def _operation_detail(
    index: int,
    row: pd.Series,
    styles: dict[str, ParagraphStyle],
    report_quantity: float,
) -> list[object]:
    sequence = _text(row.get("ucoPartOperationLineID"), str(index))
    process = _text(row.get("ucoOperationID"), "Unspecified process")
    description = _text(row.get("ucoOperationDescription"), "No description")
    work_center = _text(row.get("ucoWorkCenterID"), "Unassigned")
    external = _bool(row.get("ucoExternalJob"))
    per_assembly, operation_quantity, batches, resets = _operation_quantities(row, report_quantity)
    raw = _float(row.get("ucoLineRawCost"))
    priced = _float(row.get("ucoLineMarkedUpCost"))

    flow: list[object] = [
        CondPageBreak(2.8 * inch),
        KeepTogether(
            [
                Paragraph(
                    f"{escape(sequence)}. {escape(process)} - {escape(description)}",
                    styles["subsection"],
                ),
                _rule(thickness=0.35, space_after=3),
            ]
        ),
        Paragraph(
            escape(
                f"Work center: {work_center} | Demand: {_number(per_assembly)}/part x "
                f"{_number(report_quantity)} parts = {_number(operation_quantity)} units."
            ),
            styles["body"],
        ),
    ]

    if external:
        po = _text(row.get("ucoLastPO"), "not recorded")
        po_date = _date(row.get("ucoLastPODate"))
        unit = _float(row.get("ucoExternalUnitCost"))
        external_raw = _float(row.get("ucoExternalOperationRawCost"))
        multiplier = _float(row.get("ucoExternalOperationMarkup")) or 1
        external_priced = _float(row.get("ucoExternalOperationMarkedUpCost"))
        explanation = (
            f"Source: PO {po}, {po_date} | {_number(operation_quantity)} units x {_money(unit, 4)} "
            f"= {_money(external_raw)} raw; x {_factor(multiplier)} = {_money(external_priced)}."
        )
        cost_explanation: list[object] = [Paragraph(escape(explanation), styles["body"])]
    else:
        setup_hours = _float(row.get("ucoSetupTimeHours"))
        cycle_hours = _float(row.get("ucoCycleTimeHours"))
        reset_hours = _float(row.get("ucoBatchResetTimeHours"))
        idle_hours = _float(row.get("ucoBatchIdleTimeHours"))
        after_hours = _float(row.get("ucoAfterHoursIdleTimeHours"))
        running_hours = cycle_hours * operation_quantity
        occupied_hours = setup_hours + running_hours + resets * (reset_hours + idle_hours)
        setup_rate = _float(row.get("ucoSetupLaborRate"))
        reset_rate = _float(row.get("ucoBatchResetLaborRate"))
        occupied_rate = _float(row.get("ucoMachineOccupiedHourlyCost"))
        running_rate = _float(row.get("ucoMachineRunningHourlyCost"))
        after_multiplier = _float(row.get("ucoAfterHoursIdleRateMultiplier")) or 1
        labor_raw = _float(row.get("ucoLaborRawCost"))
        machine_raw = _float(row.get("ucoMachineRawCost"))
        quantity_rows = [
            ["Driver", "Calculation", "Result"],
            ["Batches", f"Ceiling({_number(operation_quantity)} processed units / {_number(row.get('ucoBatchSize'))} batch size)", _number(batches)],
            ["Batch resets", f"Maximum({_number(batches)} batches - 1, 0)", _number(resets)],
            ["Running time", f"{_number(operation_quantity)} units x {_number(cycle_hours, 6)} cycle hr/unit", f"{_number(running_hours, 4)} hr"],
            ["Occupied time", f"{_number(setup_hours)} setup + {_number(running_hours)} running + {_number(resets)} x ({_number(reset_hours)} reset + {_number(idle_hours)} idle)", f"{_number(occupied_hours, 4)} hr"],
            ["After-hours idle", "Saved scheduling result", f"{_number(after_hours, 4)} hr"],
        ]
        labor_formula = (
            f"Labor: ({_number(setup_hours)} setup hr x {_money(setup_rate, 2)}/hr) + "
            f"({_number(resets)} resets x {_number(reset_hours)} hr x {_money(reset_rate, 2)}/hr) = {_money(labor_raw)} raw."
        )
        machine_formula = (
            f"Machine: ({_number(occupied_hours)} occupied hr x {_money(occupied_rate, 2)}/hr) + "
            f"({_number(after_hours)} after-hours hr x {_money(occupied_rate, 2)}/hr x {_number(after_multiplier)}) + "
            f"({_number(running_hours)} running hr x {_money(running_rate, 2)}/hr) = {_money(machine_raw)} raw."
        )
        flow.append(
            _plain_table(quantity_rows, [1.25 * inch, 4.8 * inch, 1.25 * inch], header=True, repeat_rows=1, right_columns=(2,))
        )
        cost_explanation = [
                Spacer(1, 0.03 * inch),
                Paragraph(escape(labor_formula), styles["body"]),
                Paragraph(escape(machine_formula), styles["body"]),
        ]

    result_rows: list[list[object]] = [["Cost component", "Raw cost", "Factor", "Calculated price"]]
    for label, raw_key, priced_key, factor_key in (
        ("Machine", "ucoMachineRawCost", "ucoMachineMarkedUpCost", "ucoMachineCostMarkup"),
        ("Labor", "ucoLaborRawCost", "ucoLaborMarkedUpCost", "ucoLaborMarkup"),
        ("Outside processing", "ucoExternalOperationRawCost", "ucoExternalOperationMarkedUpCost", "ucoExternalOperationMarkup"),
        ("Additional", "ucoAdditionalCostRawCost", "ucoAdditionalCostMarkedUpCost", "ucoAdditionalCostMarkup"),
    ):
        bucket_raw = _float(row.get(raw_key))
        bucket_priced = _float(row.get(priced_key))
        if bucket_raw or bucket_priced:
            result_rows.append([label, _money(bucket_raw), _factor(row.get(factor_key)), _money(bucket_priced)])
    result_rows.append(["Operation contribution", _money(raw), _factor(priced / raw) if raw else "-", _money(priced)])
    flow.append(
        KeepTogether(
            [
                *cost_explanation,
                _plain_table(
                    result_rows,
                    [3.65 * inch, 1.15 * inch, 1.05 * inch, 1.45 * inch],
                    header=True,
                    repeat_rows=1,
                    right_columns=(1, 2, 3),
                    bold_last=True,
                ),
            ]
        )
    )
    return flow


def _operations_section(rows: pd.DataFrame, styles: dict[str, ParagraphStyle], report_quantity: float) -> list[object]:
    flow: list[object] = [
        KeepTogether(
            [
                Paragraph("Operation cost build-up", styles["section"]),
                _rule(),
                Paragraph(
                    "Saved routing sequence with time and rate equations for internal work and PO pricing for outside work.",
                    styles["body"],
                ),
            ]
        ),
    ]
    if rows.empty:
        flow.append(Paragraph("No operations were saved with this costing run.", styles["body"]))
        return flow
    for display_index, (_, row) in enumerate(rows.iterrows(), start=1):
        flow.extend(_operation_detail(display_index, row, styles, report_quantity))
    return flow


def _sum(rows: pd.DataFrame, column: str) -> float:
    if rows.empty or column not in rows.columns:
        return 0.0
    return float(pd.to_numeric(rows[column], errors="coerce").fillna(0).sum())


def _reconciliation(
    part: pd.Series,
    operations: pd.DataFrame,
    materials: pd.DataFrame,
    styles: dict[str, ParagraphStyle],
) -> list[object]:
    mappings = [
        ("Materials", "ucpMaterialsRawCost", "ucpMaterialsMarkedUpCost", "ucmMaterialsRawCost", "ucmMaterialsMarkedUpCost", None, None),
        ("Machine", "ucpMachineTimeRawCost", "ucpMachineTimeMarkedUpCost", "ucmMachineTimeRawCost", "ucmMachineTimeMarkedUpCost", "ucoMachineRawCost", "ucoMachineMarkedUpCost"),
        ("Labor", "ucpLaborRawCost", "ucpLaborMarkedUpCost", "ucmLaborRawCost", "ucmLaborMarkedUpCost", "ucoLaborRawCost", "ucoLaborMarkedUpCost"),
        ("Outside processing", "ucpExternalOperationsRawCost", "ucpExternalOperationsMarkedUpCost", "ucmExternalOperationsRawCost", "ucmExternalOperationsMarkedUpCost", "ucoExternalOperationRawCost", "ucoExternalOperationMarkedUpCost"),
        ("Additional", "ucpAdditionalRawCost", "ucpAdditionalMarkedUpCost", "ucmAdditionalRawCost", "ucmAdditionalMarkedUpCost", "ucoAdditionalCostRawCost", "ucoAdditionalCostMarkedUpCost"),
    ]
    data: list[list[object]] = [["Bucket", "Header raw", "Lines raw", "Variance", "Header price", "Lines price", "Variance"]]
    line_raw_total = 0.0
    line_price_total = 0.0
    for label, header_raw_key, header_price_key, material_raw_key, material_price_key, op_raw_key, op_price_key in mappings:
        header_raw = _float(part.get(header_raw_key))
        header_price = _float(part.get(header_price_key))
        line_raw = _sum(materials, material_raw_key) + (_sum(operations, op_raw_key) if op_raw_key else 0)
        line_price = _sum(materials, material_price_key) + (_sum(operations, op_price_key) if op_price_key else 0)
        line_raw_total += line_raw
        line_price_total += line_price
        data.append([label, _money(header_raw), _money(line_raw), _money(header_raw - line_raw), _money(header_price), _money(line_price), _money(header_price - line_price)])
    header_raw_total = _float(part.get("ucpTotalRawCost"))
    header_price_total = _float(part.get("ucpTotalMarkedUpCost"))
    data.append(["Total", _money(header_raw_total), _money(line_raw_total), _money(header_raw_total - line_raw_total), _money(header_price_total), _money(line_price_total), _money(header_price_total - line_price_total)])
    audit = KeepTogether(
        [
            Paragraph("Reconciliation and review flags", styles["section"]),
            _rule(),
            Paragraph(
                "This audit ties the saved header totals back to the saved material and operation lines. Non-zero variance indicates an inconsistent saved snapshot that should not be used for quoting.",
                styles["body"],
            ),
            _plain_table(
                data,
                [1.2 * inch, 1.0 * inch, 1.0 * inch, 0.9 * inch, 1.1 * inch, 1.1 * inch, 1.0 * inch],
                header=True,
                repeat_rows=1,
                right_columns=(1, 2, 3, 4, 5, 6),
                bold_last=True,
                font_size=6.8,
            ),
        ]
    )
    return [
        audit,
        *_review_flags(operations, materials, styles),
    ]


def _review_flags(operations: pd.DataFrame, materials: pd.DataFrame, styles: dict[str, ParagraphStyle]) -> list[object]:
    flags: list[str] = []
    for _, row in materials.iterrows():
        material = _text(row.get("ucmMaterialID"), "unidentified material")
        source = _text(row.get("ucmCostSource"), "").strip()
        if source == "manual_override":
            flags.append(f"{material}: uses a manual unit-cost override.")
        if source == "manufactured_history" and not _bool(row.get("ucmManufacturedPartCostIsCurrent")):
            flags.append(f"{material}: uses a non-current historical manufactured-part cost.")
        if _float(row.get("ucmUnitCost")) == 0 and _bool(row.get("ucmBackflush"), default=True):
            flags.append(f"{material}: included with a zero unit cost.")
    for _, row in operations.iterrows():
        operation = _text(row.get("ucoPartOperationLineID"), _text(row.get("ucoOperationID")))
        if _bool(row.get("ucoExternalJob")) and _text(row.get("ucoLastPO"), "") == "":
            flags.append(f"Operation {operation}: outside processing has no purchase-order reference.")
        if _float(row.get("ucoLineRawCost")) == 0:
            flags.append(f"Operation {operation}: contributes zero raw cost.")
    if not flags:
        flags.append("No automatic source-quality flags were found in the saved lines.")
    return [
        Paragraph("Review flags", styles["subsection"]),
        *[Paragraph(f"- {escape(flag)}", styles["body"]) for flag in flags],
    ]


def _notes(row: pd.Series, styles: dict[str, ParagraphStyle]) -> list[object]:
    notes = _text(row.get("ucpNotes"), "")
    if not notes:
        return []
    return [
        Paragraph("Internal notes", styles["section"]),
        _rule(),
        Paragraph(escape(notes).replace("\n", "<br/>"), styles["body"]),
    ]


def _customer_price(row: pd.Series, styles: dict[str, ParagraphStyle]) -> list[object]:
    quantity = _float(row.get("ucpCostQuantity"))
    unit_price = _float(row.get("ucpUnitMarkedUpCost"))
    total_price = _float(row.get("ucpTotalMarkedUpCost"))
    data = [
        [Paragraph("QUANTITY", styles["eyebrow"]), Paragraph("UNIT PRICE", styles["eyebrow"]), Paragraph("EXTENDED PRICE", styles["eyebrow"])],
        [Paragraph(_number(quantity), styles["price"]), Paragraph(_money(unit_price, 4), styles["price"]), Paragraph(_money(total_price), styles["price"])],
    ]
    table = _plain_table(data, [1.7 * inch, 2.5 * inch, 3.1 * inch], right_columns=(0, 1, 2), padding=5)
    table.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, 0), 0.9, BLACK), ("LINEBELOW", (0, -1), (-1, -1), 0.9, BLACK)]))
    return [
        Paragraph("Pricing basis", styles["section"]),
        table,
        Paragraph(
            "Pricing is based on the complete quantity shown. A different order quantity may change material purchasing, setup allocation, processing time, and unit price.",
            styles["small"],
        ),
    ]


def _customer_materials(
    rows: pd.DataFrame,
    styles: dict[str, ParagraphStyle],
    report_quantity: float,
) -> list[object]:
    flow: list[object] = [Paragraph("Itemized material charges", styles["section"]), _rule()]
    if rows.empty:
        flow.append(Paragraph("No backflushed material charges.", styles["body"]))
        return flow
    data: list[list[object]] = [["Item / description", "Qty/part", "Unit charge", "Extended charge"]]
    for _, row in rows.iterrows():
        charge = _float(row.get("ucmMarkedUpCost"))
        data.append(
            [
                _summary_name(row.get("ucmMaterialID"), row.get("ucmMaterialDescription"), styles),
                Paragraph(_number(row.get("ucmQtyPerAssembly")), styles["small_right"]),
                _money(charge / report_quantity, 4) if report_quantity else "-",
                _money(charge),
            ]
        )
    subtotal = _sum(rows, "ucmMarkedUpCost")
    data.append(["Material subtotal", "", _money(subtotal / report_quantity, 4) if report_quantity else "-", _money(subtotal)])
    flow.append(
        _plain_table(
            data,
            [4.15 * inch, 0.8 * inch, 1.1 * inch, 1.25 * inch],
            header=True,
            repeat_rows=1,
            right_columns=(1, 2, 3),
            bold_last=True,
        )
    )
    return flow


def _customer_operations(
    rows: pd.DataFrame,
    styles: dict[str, ParagraphStyle],
    report_quantity: float,
) -> list[object]:
    flow: list[object] = [Paragraph("Itemized operation charges", styles["section"]), _rule()]
    if rows.empty:
        flow.append(Paragraph("No operation charges.", styles["body"]))
        return flow
    data: list[list[object]] = [["Operation / description", "Performed by", "Unit charge", "Extended charge"]]
    for _, row in rows.iterrows():
        charge = _float(row.get("ucoLineMarkedUpCost"))
        data.append(
            [
                _summary_name(
                    f"{_text(row.get('ucoPartOperationLineID'))} / {_text(row.get('ucoOperationID'))}",
                    row.get("ucoOperationDescription"),
                    styles,
                ),
                "Qualified supplier" if _bool(row.get("ucoExternalJob")) else "In-house",
                _money(charge / report_quantity, 4) if report_quantity else "-",
                _money(charge),
            ]
        )
    subtotal = _sum(rows, "ucoLineMarkedUpCost")
    data.append(["Operation subtotal", "", _money(subtotal / report_quantity, 4) if report_quantity else "-", _money(subtotal)])
    flow.append(
        _plain_table(
            data,
            [4.15 * inch, 0.8 * inch, 1.1 * inch, 1.25 * inch],
            header=True,
            repeat_rows=1,
            right_columns=(2, 3),
            bold_last=True,
        )
    )
    return flow


def _customer_receipt_total(
    part: pd.Series,
    materials: pd.DataFrame,
    operations: pd.DataFrame,
    styles: dict[str, ParagraphStyle],
) -> list[object]:
    quantity = _float(part.get("ucpCostQuantity"))
    material_total = _sum(materials, "ucmMarkedUpCost")
    operation_total = _sum(operations, "ucoLineMarkedUpCost")
    total = _float(part.get("ucpTotalMarkedUpCost"))
    other = total - material_total - operation_total
    data: list[list[object]] = [["Charge group", "Unit charge", "Extended charge"]]
    data.append(["Materials", _money(material_total / quantity, 4) if quantity else "-", _money(material_total)])
    data.append(["Operations", _money(operation_total / quantity, 4) if quantity else "-", _money(operation_total)])
    if abs(other) >= 0.005:
        data.append(["Other saved charges", _money(other / quantity, 4) if quantity else "-", _money(other)])
    data.append(["Total", _money(total / quantity, 4) if quantity else "-", _money(total)])
    return [
        Paragraph("Receipt total", styles["section"]),
        _rule(),
        _plain_table(
            data,
            [4.95 * inch, 1.1 * inch, 1.25 * inch],
            header=True,
            repeat_rows=1,
            right_columns=(1, 2),
            bold_last=True,
        ),
    ]


def _page_decorations(
    canvas,
    doc,
    *,
    part_id: str,
    part_cost_id: str,
    audience: str,
    company_name: str,
) -> None:
    canvas.saveState()
    title = "Internal Cost Analysis" if audience == ReportAudience.INTERNAL else "Customer Cost Summary"
    canvas.setTitle(f"{title} - {part_id}")
    canvas.setAuthor(company_name)
    canvas.setStrokeColor(BLACK)
    canvas.setLineWidth(0.35)
    canvas.line(doc.leftMargin, 0.48 * inch, PAGE_WIDTH - doc.rightMargin, 0.48 * inch)
    canvas.setFillColor(BLACK)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(doc.leftMargin, 0.29 * inch, f"{company_name} | Part {part_id} | Run {part_cost_id}")
    canvas.drawRightString(PAGE_WIDTH - doc.rightMargin, 0.29 * inch, f"Page {doc.page}")
    canvas.restoreState()


def _build_document(
    story: list[object],
    row: pd.Series,
    *,
    audience: str,
    company_name: str,
) -> bytes:
    part_id = _text(row.get("ucpPartID"), "part")
    part_cost_id = _text(row.get("ucpPartCostID"), "unsaved")
    buffer = BytesIO()
    title = "Internal Cost Analysis" if audience == ReportAudience.INTERNAL else "Customer Cost Summary"
    doc = SimpleDocTemplate(
        buffer,
        pagesize=PAGE_SIZE,
        rightMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.65 * inch,
        title=f"{title} - {part_id}",
        author=company_name,
        subject=f"Saved costing run {part_cost_id}",
    )
    callback = lambda canvas, current_doc: _page_decorations(
        canvas,
        current_doc,
        part_id=part_id,
        part_cost_id=part_cost_id,
        audience=audience,
        company_name=company_name,
    )
    doc.build(story, onFirstPage=callback, onLaterPages=callback)
    result = buffer.getvalue()
    if not result.startswith(b"%PDF-"):
        raise RuntimeError("ReportLab returned an invalid PDF")
    return result


def render_internal_part_cost_document(
    part_cost: pd.DataFrame,
    operation_lines: pd.DataFrame,
    material_lines: pd.DataFrame,
    *,
    company_name: str = "Meziere Enterprises",
) -> bytes:
    """Return the full cost-audit document for internal decision makers."""
    if part_cost.empty:
        raise ValueError("A saved part cost is required to render the report")
    row = part_cost.iloc[0]
    styles = _styles()
    quantity = _float(row.get("ucpCostQuantity"))
    included_materials = _backflushed_materials(material_lines)
    story: list[object] = [
        Paragraph("INTERNAL - COSTING SOURCE AND CALCULATION RECORD", styles["eyebrow"]),
        Paragraph("Internal Cost Analysis", styles["title"]),
        Paragraph(
            "A self-contained explanation of the saved material, labor, machine, outside-processing, and additional costs used to calculate this part price.",
            styles["subtitle"],
        ),
        _rule(thickness=0.9),
        _identity_table(row, styles, internal=True),
        *_internal_conclusion(row, styles),
        *_internal_line_summary(included_materials, operation_lines, styles),
        PageBreak(),
        *_materials_section(included_materials, styles, quantity),
        *_operations_section(operation_lines, styles, quantity),
        *_reconciliation(row, operation_lines, included_materials, styles),
        *_notes(row, styles),
    ]
    return _build_document(story, row, audience=ReportAudience.INTERNAL, company_name=company_name)


def render_customer_part_cost_document(
    part_cost: pd.DataFrame,
    operation_lines: pd.DataFrame,
    material_lines: pd.DataFrame,
    *,
    company_name: str = "Meziere Enterprises",
) -> bytes:
    """Return a customer-safe summary without internal rates, sources, or margins."""
    if part_cost.empty:
        raise ValueError("A saved part cost is required to render the report")
    row = part_cost.iloc[0]
    styles = _styles()
    quantity = _float(row.get("ucpCostQuantity"))
    included_materials = _backflushed_materials(material_lines)
    story: list[object] = [
        Paragraph(escape(company_name.upper()), styles["eyebrow"]),
        Paragraph("Customer Cost Summary", styles["customer_title"]),
        Paragraph(
            "Product, quantity, pricing, material content, and manufacturing scope represented by this costing record.",
            styles["subtitle"],
        ),
        _rule(thickness=0.9),
        _identity_table(row, styles, internal=False),
        *_customer_price(row, styles),
        *_customer_materials(included_materials, styles, quantity),
        *_customer_operations(operation_lines, styles, quantity),
        *_customer_receipt_total(row, included_materials, operation_lines, styles),
    ]
    return _build_document(story, row, audience=ReportAudience.CUSTOMER, company_name=company_name)


def render_part_cost_document(
    part_cost: pd.DataFrame,
    operation_lines: pd.DataFrame,
    material_lines: pd.DataFrame,
) -> bytes:
    """Backward-compatible alias for the internal cost analysis."""
    return render_internal_part_cost_document(part_cost, operation_lines, material_lines)
