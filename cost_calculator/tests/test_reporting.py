from io import BytesIO
import unittest
from unittest.mock import patch

import pandas as pd
from fastapi import HTTPException
from pypdf import PdfReader

from reporting import ReportRenderError, render_part_cost_document, render_part_cost_pdf
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
                "ucoExternalJob": False,
                "ucoLineRawCost": 165.00,
                "ucoLineMarkedUpCost": 189.75,
            }
            for index in range(count)
        ]
    )


def pdf_text(pdf: bytes) -> tuple[PdfReader, str]:
    reader = PdfReader(BytesIO(pdf))
    return reader, "\n".join(page.extract_text() or "" for page in reader.pages)


class ReportLabRendererTests(unittest.TestCase):
    def test_saved_cost_renders_as_a_valid_complete_pdf(self):
        pdf = render_part_cost_document(part_cost_frame(), operation_frame(), material_frame())
        reader, text = pdf_text(pdf)

        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertGreaterEqual(len(reader.pages), 1)
        for expected in (
            "Part Cost Report",
            "ABC-123",
            "Billet adapter <production>",
            "Cost summary",
            "Materials",
            "AL-6061-1",
            "Operations",
            "Machine profile and finish bores",
            "Approved for quoting",
        ):
            self.assertIn(expected, text)

    def test_long_tables_paginate_and_repeat_column_headers(self):
        pdf = render_part_cost_document(
            part_cost_frame(),
            operation_frame(80),
            material_frame(55),
        )
        reader, text = pdf_text(pdf)

        self.assertGreater(len(reader.pages), 2)
        self.assertGreater(text.count("Material"), 1)
        self.assertGreater(text.count("Work center"), 1)
        self.assertEqual(text.count("AL-6061-"), 55)
        self.assertEqual(text.count("OP20"), 80)
        for page in reader.pages[1:]:
            page_text = page.extract_text() or ""
            if "AL-6061" in page_text:
                self.assertIn("Description", page_text)
                self.assertIn("Unit cost", page_text)
            if "OP20" in page_text:
                self.assertIn("Work center", page_text)
                self.assertIn("Marked up", page_text)

    def test_facade_loads_saved_lines_for_the_requested_id(self):
        with patch("utils.queries.get_part_cost", return_value=part_cost_frame()) as get_cost, patch(
            "utils.queries.get_saved_operation_lines", return_value=operation_frame()
        ) as get_operations, patch(
            "utils.queries.get_saved_material_lines", return_value=material_frame()
        ) as get_materials:
            pdf = render_part_cost_pdf(42)

        self.assertTrue(pdf.startswith(b"%PDF-"))
        get_cost.assert_called_once_with(42)
        get_operations.assert_called_once_with(42)
        get_materials.assert_called_once_with(42)

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
            'inline; filename="ABC-123-cost-42.pdf"',
        )
        render.assert_called_once_with(42, part_cost=part_cost)

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
