from io import BytesIO
import unittest
from unittest.mock import patch

import pandas as pd
from fastapi import HTTPException
from pypdf import PdfReader

from reporting import (
    ReportAudience,
    ReportRenderError,
    render_customer_part_cost_document,
    render_internal_part_cost_document,
    render_part_cost_pdf,
)
from web.routers import reports


def part_cost_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ucpPartCostID": 42,
                "ucpPartID": "ABC-123",
                "ucpPartRevision": "B",
                "ucpPartDescription": "Billet adapter <production>",
                "ucpCostQuantity": 100,
                "ucpDateCosted": pd.Timestamp("2026-08-03T12:30:00"),
                "ucpCostedBy": "report-user",
                "ucpIsCurrent": True,
                "ucpMaterialsRawCost": 180.25,
                "ucpMaterialsMarkedUpCost": 216.30,
                "ucpMachineTimeRawCost": 90.00,
                "ucpMachineTimeMarkedUpCost": 103.50,
                "ucpLaborRawCost": 75.00,
                "ucpLaborMarkedUpCost": 86.25,
                "ucpExternalOperationsRawCost": 25.00,
                "ucpExternalOperationsMarkedUpCost": 31.25,
                "ucpAdditionalRawCost": 10.00,
                "ucpAdditionalMarkedUpCost": 11.50,
                "ucpTotalRawCost": 380.25,
                "ucpTotalMarkedUpCost": 448.80,
                "ucpUnitRawCost": 3.8025,
                "ucpUnitMarkedUpCost": 4.488,
                "ucpRetailUnitPrice": 8.99,
                "ucpNotes": "Review setup assumptions.\nApproved for quoting.",
            }
        ]
    )


def material_frame(count: int = 1) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ucmMaterialID": f"AL-6061-{index + 1}",
                "ucmMaterialDescription": "Aluminum round bar",
                "ucmQtyPerAssembly": 1.25,
                "ucmTotalQuantityRequired": 125,
                "ucmCostSource": "Last PO",
                "ucmUnitCost": 1.442,
                "ucmIsPurchased": True,
                "ucmBackflush": True,
                "ucmLastPO": f"PO-100{index + 1}-1",
                "ucmLastPODate": pd.Timestamp("2026-07-15"),
                "ucmLastPOPurchaseUnitCost": 11.536,
                "ucmLastPOConversionFactor": 0.125,
                "ucmLastPOPurchaseUnit": "BAR",
                "ucmLastPOInventoryUnit": "EA",
                "ucmMinimumPurchaseQty": 25,
                "ucmWasteQuantity": 0,
                "ucmMaterialMarkup": 1.2,
                "ucmMaterialsRawCost": 180.25,
                "ucmMaterialsMarkedUpCost": 216.30,
                "ucmRawCost": 180.25,
                "ucmMarkedUpCost": 216.30,
            }
            for index in range(count)
        ]
    )


def operation_frame(count: int = 1) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ucoPartOperationLineID": (index + 1) * 10,
                "ucoWorkCenterID": "MILL",
                "ucoOperationID": "OP20",
                "ucoOperationDescription": "Machine profile and finish bores",
                "ucoSetupTimeHours": 1.5,
                "ucoCycleTimeHours": 0.08,
                "ucoCostQuantity": 100,
                "ucoQuantityPerAssembly": 1,
                "ucoBatchSize": 25,
                "ucoBatchResetTimeHours": 0.1,
                "ucoBatchIdleTimeHours": 0.05,
                "ucoAfterHoursIdleTimeHours": 0,
                "ucoAfterHoursIdleRateMultiplier": 1,
                "ucoSetupLaborRate": 25,
                "ucoBatchResetLaborRate": 25,
                "ucoLaborMarkup": 1.15,
                "ucoMachineRunningHourlyCost": 10,
                "ucoMachineOccupiedHourlyCost": 5,
                "ucoMachineCostMarkup": 1.15,
                "ucoExternalJob": False,
                "ucoMachineRawCost": 90,
                "ucoMachineMarkedUpCost": 103.50,
                "ucoLaborRawCost": 75,
                "ucoLaborMarkedUpCost": 86.25,
                "ucoExternalOperationRawCost": 0,
                "ucoExternalOperationMarkedUpCost": 0,
                "ucoAdditionalCostRawCost": 0,
                "ucoAdditionalCostMarkedUpCost": 0,
                "ucoLineRawCost": 165.00,
                "ucoLineMarkedUpCost": 189.75,
            }
            for index in range(count)
        ]
    )


def representative_report_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Exercise the major source and calculation paths in visual QA and tests."""
    part = part_cost_frame().astype(object)
    materials = material_frame(3).astype(object)
    operations = operation_frame(5).astype(object)

    materials.loc[
        1,
        [
            "ucmMaterialID",
            "ucmMaterialDescription",
            "ucmCostSource",
            "ucmIsPurchased",
            "ucmManufacturedPartCostID",
            "ucmManufacturedPartCostIsCurrent",
            "ucmLastPO",
        ],
    ] = ["SUB-ASSY-20", "Machined valve subassembly", "manufactured_current", False, 317, True, None]
    materials.loc[
        1,
        [
            "ucmMaterialsRawCost",
            "ucmMachineTimeRawCost",
            "ucmLaborRawCost",
            "ucmExternalOperationsRawCost",
            "ucmAdditionalRawCost",
        ],
    ] = [70, 45, 35, 20, 10]
    materials.loc[
        1,
        [
            "ucmMaterialsMarkedUpCost",
            "ucmMachineTimeMarkedUpCost",
            "ucmLaborMarkedUpCost",
            "ucmExternalOperationsMarkedUpCost",
            "ucmAdditionalMarkedUpCost",
        ],
    ] = [84, 54, 42, 24, 12]
    materials.loc[1, ["ucmRawCost", "ucmMarkedUpCost", "ucmUnitCost"]] = [180, 216, 1.44]
    materials.loc[
        2,
        [
            "ucmMaterialID",
            "ucmMaterialDescription",
            "ucmCostSource",
            "ucmIsPurchased",
            "ucmUnitCost",
            "ucmMaterialsRawCost",
            "ucmMaterialsMarkedUpCost",
            "ucmRawCost",
            "ucmMarkedUpCost",
        ],
    ] = ["PACK-01", "Protective packaging set", "manual_override", False, 0.35, 43.75, 52.50, 43.75, 52.50]

    operations.loc[
        2,
        [
            "ucoPartOperationLineID",
            "ucoOperationID",
            "ucoOperationDescription",
            "ucoWorkCenterID",
            "ucoExternalJob",
            "ucoLastPO",
            "ucoLastPODate",
            "ucoExternalUnitCost",
            "ucoExternalCost",
            "ucoExternalOperationMarkup",
            "ucoExternalOperationRawCost",
            "ucoExternalOperationMarkedUpCost",
            "ucoMachineRawCost",
            "ucoMachineMarkedUpCost",
            "ucoLaborRawCost",
            "ucoLaborMarkedUpCost",
            "ucoLineRawCost",
            "ucoLineMarkedUpCost",
        ],
    ] = [30, "ANODIZE", "Black hard anodize and seal", "OUTSIDE", True, "PO-88214-3", "2026-07-22", 0.85, 85, 1.25, 85, 106.25, 0, 0, 0, 0, 85, 106.25]

    bucket_map = [
        ("ucpMaterialsRawCost", "ucpMaterialsMarkedUpCost", "ucmMaterialsRawCost", "ucmMaterialsMarkedUpCost", None, None),
        ("ucpMachineTimeRawCost", "ucpMachineTimeMarkedUpCost", "ucmMachineTimeRawCost", "ucmMachineTimeMarkedUpCost", "ucoMachineRawCost", "ucoMachineMarkedUpCost"),
        ("ucpLaborRawCost", "ucpLaborMarkedUpCost", "ucmLaborRawCost", "ucmLaborMarkedUpCost", "ucoLaborRawCost", "ucoLaborMarkedUpCost"),
        ("ucpExternalOperationsRawCost", "ucpExternalOperationsMarkedUpCost", "ucmExternalOperationsRawCost", "ucmExternalOperationsMarkedUpCost", "ucoExternalOperationRawCost", "ucoExternalOperationMarkedUpCost"),
        ("ucpAdditionalRawCost", "ucpAdditionalMarkedUpCost", "ucmAdditionalRawCost", "ucmAdditionalMarkedUpCost", "ucoAdditionalCostRawCost", "ucoAdditionalCostMarkedUpCost"),
    ]
    raw_total = 0.0
    price_total = 0.0
    for header_raw, header_price, material_raw, material_price, operation_raw, operation_price in bucket_map:
        raw = materials[material_raw].fillna(0).sum() + (operations[operation_raw].fillna(0).sum() if operation_raw else 0)
        price = materials[material_price].fillna(0).sum() + (operations[operation_price].fillna(0).sum() if operation_price else 0)
        part.loc[0, header_raw] = raw
        part.loc[0, header_price] = price
        raw_total += raw
        price_total += price
    quantity = part.loc[0, "ucpCostQuantity"]
    part.loc[0, "ucpTotalRawCost"] = raw_total
    part.loc[0, "ucpTotalMarkedUpCost"] = price_total
    part.loc[0, "ucpUnitRawCost"] = raw_total / quantity
    part.loc[0, "ucpUnitMarkedUpCost"] = price_total / quantity
    return part, operations, materials


def pdf_text(pdf: bytes) -> tuple[PdfReader, str]:
    reader = PdfReader(BytesIO(pdf))
    return reader, "\n".join(page.extract_text() or "" for page in reader.pages)


class ReportLabRendererTests(unittest.TestCase):
    def test_internal_report_is_a_portrait_monochrome_cost_audit(self):
        pdf = render_internal_part_cost_document(part_cost_frame(), operation_frame(), material_frame())
        reader, text = pdf_text(pdf)

        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertGreaterEqual(len(reader.pages), 1)
        self.assertLess(float(reader.pages[0].mediabox.width), float(reader.pages[0].mediabox.height))
        for expected in (
            "Internal Cost Analysis",
            "ABC-123",
            "Billet adapter <production>",
            "Cost conclusion",
            "Costed line summary",
            "Material cost build-up",
            "Source: PO PO-1001-1",
            "AL-6061-1",
            "Operation cost build-up",
            "Machine profile and finish bores",
            "Labor:",
            "Machine:",
            "Reconciliation and review flags",
            "Approved for quoting",
        ):
            self.assertIn(expected, text)

    def test_customer_report_itemizes_charges_without_internal_cost_inputs(self):
        pdf = render_customer_part_cost_document(part_cost_frame(), operation_frame(), material_frame())
        reader, text = pdf_text(pdf)

        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertLess(float(reader.pages[0].mediabox.width), float(reader.pages[0].mediabox.height))
        for expected in (
            "Customer Cost Summary",
            "Pricing basis",
            "Itemized material charges",
            "Itemized operation charges",
            "Receipt total",
            "$2.1630",
            "$216.30",
            "$1.8975",
            "$189.75",
            "$4.4880",
            "$448.80",
        ):
            self.assertIn(expected, text)
        for internal_only in (
            "Raw cost",
            "Effective factor",
            "PO-1001-1",
            "$25.00/hr",
            "Review setup assumptions",
            "Basis and limitations",
        ):
            self.assertNotIn(internal_only, text)

    def test_internal_report_explains_manufactured_and_outside_sources(self):
        part, operations, materials = representative_report_frames()
        _, text = pdf_text(render_internal_part_cost_document(part, operations, materials))

        self.assertIn("Source: manufactured cost run 317 (current)", text)
        self.assertIn("Source: PO PO-88214-3", text)
        self.assertIn("PACK-01: uses a manual unit-cost override", text)

        _, customer_text = pdf_text(render_customer_part_cost_document(part, operations, materials))
        self.assertIn("PACK-01", customer_text)
        self.assertIn("$0.5250", customer_text)
        self.assertIn("$52.50", customer_text)
        self.assertNotIn("PO-88214-3", customer_text)

    def test_reconciliation_uses_persisted_material_line_totals(self):
        part = part_cost_frame().astype(object)
        part.loc[
            0,
            [
                "ucpMaterialsRawCost",
                "ucpMaterialsMarkedUpCost",
                "ucpMachineTimeRawCost",
                "ucpMachineTimeMarkedUpCost",
                "ucpLaborRawCost",
                "ucpLaborMarkedUpCost",
                "ucpExternalOperationsRawCost",
                "ucpExternalOperationsMarkedUpCost",
                "ucpAdditionalRawCost",
                "ucpAdditionalMarkedUpCost",
                "ucpTotalRawCost",
                "ucpTotalMarkedUpCost",
                "ucpUnitRawCost",
                "ucpUnitMarkedUpCost",
            ],
        ] = [0.229, 0.229, 0, 0, 0, 0, 0, 0, 0, 0, 0.229, 0.229, 0.229, 0.229]
        materials = material_frame().drop(
            columns=["ucmMaterialsRawCost", "ucmMaterialsMarkedUpCost"]
        )
        materials.loc[0, ["ucmRawCost", "ucmMarkedUpCost"]] = [0.229, 0.229]

        _, text = pdf_text(
            render_internal_part_cost_document(part, pd.DataFrame(), materials)
        )

        self.assertIn("Saved material lines", text)
        self.assertRegex(text, r"(?s)Saved material lines\s+\$0\.23\s+\$0\.23")
        self.assertRegex(text, r"(?s)All saved lines\s+\$0\.23\s+\$0\.23")
        self.assertRegex(text, r"(?s)Variance\s+\$0\.00\s+\$0\.00")

    def test_small_internal_summary_keeps_every_line_on_the_first_page(self):
        part, operations, materials = representative_report_frames()
        reader, _ = pdf_text(render_internal_part_cost_document(part, operations, materials))
        first_page = reader.pages[0].extract_text() or ""

        for material_id in materials["ucmMaterialID"]:
            self.assertIn(material_id, first_page)
        for sequence in operations["ucoPartOperationLineID"]:
            self.assertIn(f"{sequence} /", first_page)

    def test_both_reports_list_every_backflushed_material_and_every_operation(self):
        part = part_cost_frame()
        materials = material_frame(5).astype(object)
        materials.loc[3, "ucmBackflush"] = False
        materials.loc[4, "ucmBackflush"] = None
        included_materials = materials.iloc[:3]["ucmMaterialID"]
        omitted_materials = materials.iloc[3:]["ucmMaterialID"]
        operations = operation_frame(6)

        for renderer in (render_internal_part_cost_document, render_customer_part_cost_document):
            _, text = pdf_text(renderer(part, operations, materials))
            for material_id in included_materials:
                self.assertIn(material_id, text)
            for material_id in omitted_materials:
                self.assertNotIn(material_id, text)
            for sequence in operations["ucoPartOperationLineID"]:
                self.assertIn(str(sequence), text)

    def test_long_internal_report_paginates_and_repeats_detail_headers(self):
        pdf = render_internal_part_cost_document(
            part_cost_frame(),
            operation_frame(18),
            material_frame(14),
        )
        reader, text = pdf_text(pdf)

        self.assertGreater(len(reader.pages), 2)
        self.assertIn("Costed line summary", reader.pages[0].extract_text() or "")
        self.assertIn("Materials (14)", reader.pages[0].extract_text() or "")
        self.assertIn("Costed line summary (continued)", reader.pages[1].extract_text() or "")
        self.assertIn("Operations (18)", reader.pages[1].extract_text() or "")
        self.assertIn("Material cost build-up", reader.pages[2].extract_text() or "")
        self.assertEqual(text.count("Source: PO"), 14)
        self.assertEqual(text.count("Work center: MILL"), 18)
        self.assertGreater(text.count("Cost component"), 2)

    def test_facade_loads_saved_lines_for_the_requested_id(self):
        with patch("utils.queries.get_part_cost", return_value=part_cost_frame()) as get_cost, patch(
            "utils.queries.get_saved_operation_lines", return_value=operation_frame()
        ) as get_operations, patch(
            "utils.queries.get_saved_material_lines", return_value=material_frame()
        ) as get_materials:
            pdf = render_part_cost_pdf(42, audience=ReportAudience.CUSTOMER)

        self.assertTrue(pdf.startswith(b"%PDF-"))
        get_cost.assert_called_once_with(42)
        get_operations.assert_called_once_with(42)
        get_materials.assert_called_once_with(42)
        _, text = pdf_text(pdf)
        self.assertIn("Customer Cost Summary", text)

    def test_empty_saved_cost_is_a_render_error(self):
        with patch("utils.queries.get_part_cost", return_value=pd.DataFrame()):
            with self.assertRaisesRegex(ReportRenderError, "not found"):
                render_part_cost_pdf(999)


class ReportRouteTests(unittest.TestCase):
    def test_report_response_opens_inline_with_safe_filename(self):
        part_cost = pd.DataFrame([{"ucpPartID": "ABC/123"}])
        with patch("web.routers.reports.get_part_cost", return_value=part_cost), patch(
            "web.routers.reports.render_part_cost_pdf", return_value=b"%PDF-1.7"
        ) as render:
            response = reports.part_cost_report(42)

        self.assertEqual(response.media_type, "application/pdf")
        self.assertEqual(response.body, b"%PDF-1.7")
        self.assertEqual(
            response.headers["content-disposition"],
            'inline; filename="ABC-123-internal-cost-42.pdf"',
        )
        render.assert_called_once_with(42, part_cost=part_cost, audience=ReportAudience.INTERNAL)

    def test_customer_report_route_uses_customer_renderer_and_filename(self):
        part_cost = pd.DataFrame([{"ucpPartID": "ABC/123"}])
        with patch("web.routers.reports.get_part_cost", return_value=part_cost), patch(
            "web.routers.reports.render_part_cost_pdf", return_value=b"%PDF-1.7"
        ) as render:
            response = reports.customer_part_cost_report(42)

        self.assertEqual(
            response.headers["content-disposition"],
            'inline; filename="ABC-123-customer-cost-42.pdf"',
        )
        render.assert_called_once_with(42, part_cost=part_cost, audience=ReportAudience.CUSTOMER)

    def test_missing_cost_is_not_rendered(self):
        with patch(
            "web.routers.reports.get_part_cost", return_value=pd.DataFrame()
        ), patch("web.routers.reports.render_part_cost_pdf") as render:
            with self.assertRaises(HTTPException) as raised:
                reports.part_cost_report(999)

        self.assertEqual(raised.exception.status_code, 404)
        render.assert_not_called()

    def test_renderer_failure_is_internal_server_error(self):
        part_cost = pd.DataFrame([{"ucpPartID": "ABC"}])
        with patch("web.routers.reports.get_part_cost", return_value=part_cost), patch(
            "web.routers.reports.render_part_cost_pdf",
            side_effect=ReportRenderError("failed"),
        ):
            with self.assertRaises(HTTPException) as raised:
                reports.part_cost_report(42)

        self.assertEqual(raised.exception.status_code, 500)


if __name__ == "__main__":
    unittest.main()
