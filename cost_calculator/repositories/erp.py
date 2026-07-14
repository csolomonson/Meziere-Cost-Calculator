"""Read-only repository for ERP-owned manufacturing data."""

import pandas as pd


def get_part(part_id, revision_id="", *, run_query):
    if revision_id:
        query = """
        SELECT TOP 1
            p.impPartID,
            r.imrPartRevisionID AS impPartRevisionID,
            r.imrShortDescription AS impPartShortDescription,
            r.imrShortDescription AS impRevisionShortDescription
        FROM Parts p
        LEFT JOIN PartRevisions r
            ON r.imrPartID = p.impPartID
            AND r.imrPartRevisionID = :param2
        WHERE p.impPartID = :param1
        ORDER BY COALESCE(r.imrInactive, 0), r.imrPartRevisionID
        """
        return run_query(query, (part_id, revision_id))

    query = """
    SELECT TOP 1
        p.impPartID,
        r.imrPartRevisionID AS impPartRevisionID,
        r.imrShortDescription AS impPartShortDescription,
        r.imrShortDescription AS impRevisionShortDescription
    FROM Parts p
    LEFT JOIN PartRevisions r
        ON r.imrPartID = p.impPartID
        AND COALESCE(r.imrInactive, 0) = 0
    WHERE p.impPartID = :param1
    ORDER BY COALESCE(r.imrInactive, 0), r.imrPartRevisionID
    """
    return run_query(query, (part_id,))


def get_bom(part_id, revision_id="", *, run_query):
    query = """
    SELECT
        immMethodID,
        immMethodRevisionID,
        immPartID,
        immPartRevisionID,
        immPartShortDescription,
        immQuantityPerAssembly,
        immEstimatedUnitCost,
        immBackflush
    FROM PartMaterials
    WHERE immMethodID = :param1
        AND immMethodRevisionID = :param2
    ORDER BY immBackflush DESC, immPartID
    """
    return run_query(query, (part_id, revision_id))


def get_operations(part_id, revision_id="", *, run_query):
    query = """
    SELECT
        imoMethodID,
        imoMethodRevisionID,
        imoWorkCenterID,
        imoProcessID,
        imoProcessShortDescription,
        imoQuantityPerAssembly,
        imoSetupHours,
        imoProductionStandard,
        imoMethodOperationID,
        imoOperationType
    FROM PartOperations
    WHERE imoMethodID = :param1
        AND imoMethodRevisionID = :param2
    ORDER BY imoMethodOperationID
    """
    return run_query(query, (part_id, revision_id))


def get_last_external_operation_po(
    part_id, revision_id, method_operation_id, *, run_query
):
    query = """
    SELECT TOP 1
        pmlPurchaseOrderID,
        pmlPurchaseOrderLineID,
        pmlPurchaseUnitCostBase,
        pmlSetupChargeBase,
        pmlTotalExtendedCostBase,
        pmlPurchaseQuantity,
        pmlPurchaseQuantityReceived,
        pmlDueDate,
        pmlCreatedDate
    FROM PurchaseOrderLines
    WHERE pmlPartID = :param1
        AND pmlPartRevisionID = :param2
        AND pmlJobOperationID = :param3
        AND pmlPurchaseQuantityReceived > 0
        AND pmlPurchaseUnitCostBase > 0
    ORDER BY
        COALESCE(pmlDueDate, pmlCreatedDate) DESC,
        pmlPurchaseOrderID DESC,
        pmlPurchaseOrderLineID DESC
    """
    return run_query(query, (part_id, revision_id, method_operation_id))


def get_last_material_po(material_id, material_revision_id="", *, run_query):
    query = """
    SELECT TOP 1
        *,
        pmlPurchaseUnitCostBase * COALESCE(NULLIF(pmlConversionFactor, 0), 1) AS pmlInventoryUnitCostBase
    FROM PurchaseOrderLines
    WHERE pmlPartID = :param1
        AND pmlPartRevisionID = :param2
        AND pmlPurchaseQuantityReceived > 0
        AND pmlPurchaseUnitCostBase > 0
    ORDER BY
        COALESCE(pmlDueDate, pmlCreatedDate) DESC,
        pmlPurchaseOrderID DESC,
        pmlPurchaseOrderLineID DESC
    """
    return run_query(query, (material_id, material_revision_id))


def search_operations(search_text, limit=12, *, run_query):
    query = """
    SELECT TOP 12
        imoWorkCenterID,
        imoProcessID,
        imoProcessShortDescription,
        imoQuantityPerAssembly,
        imoSetupHours,
        imoProductionStandard,
        imoOperationType
    FROM PartOperations
    WHERE imoProcessID LIKE :param1
        OR imoProcessShortDescription LIKE :param1
        OR imoWorkCenterID LIKE :param1
    GROUP BY
        imoWorkCenterID,
        imoProcessID,
        imoProcessShortDescription,
        imoQuantityPerAssembly,
        imoSetupHours,
        imoProductionStandard,
        imoOperationType
    ORDER BY imoProcessShortDescription
    """
    return run_query(query, (f"%{search_text}%",))


def search_work_centers(search_text, limit=12, *, run_query):
    query = """
    SELECT TOP 12
        xawWorkCenterID,
        xawDescription,
        xawProcessID,
        xawSetupHours,
        xawProductionStandard
    FROM WorkCenters
    WHERE xawWorkCenterID LIKE :param1
        OR xawDescription LIKE :param1
        OR xawProcessID LIKE :param1
    ORDER BY xawWorkCenterID
    """
    return run_query(query, (f"%{search_text}%",))


def search_processes(search_text, work_center_id="", limit=50, *, run_query):
    if work_center_id:
        query = """
        SELECT TOP 50
            p.xacProcessID AS xaoOperationID,
            p.xacShortDescription AS xaoDescription,
            p.xacSetupHours AS xaoSetupHours,
            p.xacProductionStandard AS xaoProductionStandard,
            wc.xawSetupHours,
            wc.xawProductionStandard
        FROM WorkCenters wc
        INNER JOIN Processes p
            ON p.xacProcessID = wc.xawProcessID
        WHERE wc.xawWorkCenterID = :param2
            AND (
                p.xacProcessID LIKE :param1
                OR p.xacShortDescription LIKE :param1
            )
        ORDER BY p.xacProcessID
        """
        return run_query(query, (f"%{search_text}%", work_center_id))

    query = """
    SELECT TOP 50
        xacProcessID AS xaoOperationID,
        xacShortDescription AS xaoDescription,
        xacSetupHours AS xaoSetupHours,
        xacProductionStandard AS xaoProductionStandard
    FROM Processes
    WHERE xacProcessID LIKE :param1
        OR xacShortDescription LIKE :param1
    ORDER BY xacProcessID
    """
    return run_query(query, (f"%{search_text}%",))


def get_external_operation_pos(
    part_id, revision_id, method_operation_id, *, run_query
):
    query = """
    SELECT TOP 100 *
    FROM PurchaseOrderLines
    WHERE pmlPartID = :param1
        AND pmlPartRevisionID = :param2
        AND pmlJobOperationID = :param3
    ORDER BY
        COALESCE(pmlDueDate, pmlCreatedDate) DESC,
        pmlPurchaseOrderID DESC,
        pmlPurchaseOrderLineID DESC
    """
    return run_query(query, (part_id, revision_id, method_operation_id))


def get_material_pos(material_id, material_revision_id="", *, run_query):
    if material_revision_id:
        query = """
        SELECT TOP 100
            *,
            pmlPurchaseUnitCostBase * COALESCE(NULLIF(pmlConversionFactor, 0), 1) AS pmlInventoryUnitCostBase
        FROM PurchaseOrderLines
        WHERE pmlPartID = :param1
            AND pmlPartRevisionID = :param2
        ORDER BY
            COALESCE(pmlDueDate, pmlCreatedDate) DESC,
            pmlPurchaseOrderID DESC,
            pmlPurchaseOrderLineID DESC
        """
        return run_query(query, (material_id, material_revision_id))

    query = """
    SELECT TOP 100
        *,
        pmlPurchaseUnitCostBase * COALESCE(NULLIF(pmlConversionFactor, 0), 1) AS pmlInventoryUnitCostBase
    FROM PurchaseOrderLines
    WHERE pmlPartID = :param1
    ORDER BY
        COALESCE(pmlDueDate, pmlCreatedDate) DESC,
        pmlPurchaseOrderID DESC,
        pmlPurchaseOrderLineID DESC
    """
    return run_query(query, (material_id,))


def get_current_retail_price(
    part_id, revision_id="", *, run_query, legacy_lookup
):
    query = """
    SELECT TOP 1
        pp.*,
        pb.*
    FROM PartPrices pp
    INNER JOIN PartPriceBreaks pb
        ON pb.imjPartPriceID = pp.imiPartPriceID
    WHERE pp.imiPartID = :param1
        AND COALESCE(pp.imiPartRevisionID, '') = :param2
        AND pp.imiCustomerGroupID = 'CG01'
        AND pp.imiEndDate IS NULL
    ORDER BY
        COALESCE(pp.imiStartDate, pp.imiCreatedDate, '19000101') DESC,
        pp.imiPartPriceID DESC
    """
    try:
        rows = run_query(query, (part_id, revision_id or ""))
    except Exception:
        rows = legacy_lookup(part_id, revision_id)
    return add_retail_unit_price(rows)


def get_current_retail_prices(part_id, revision_id="", *, run_query):
    query = """
    WITH priced AS (
        SELECT
            pp.imiCustomerGroupID,
            pp.imiPartPriceID,
            pp.imiPartID,
            pp.imiPartRevisionID,
            pp.imiStartDate,
            pp.imiEndDate,
            pp.imiCreatedDate,
            pb.imjUnitPrice,
            ROW_NUMBER() OVER (
                PARTITION BY pp.imiCustomerGroupID
                ORDER BY
                    COALESCE(pp.imiStartDate, pp.imiCreatedDate, '19000101') DESC,
                    pp.imiPartPriceID DESC
            ) AS row_number
        FROM PartPrices pp
        INNER JOIN PartPriceBreaks pb
            ON pb.imjPartPriceID = pp.imiPartPriceID
        WHERE pp.imiPartID = :param1
            AND COALESCE(pp.imiPartRevisionID, '') = :param2
            AND pp.imiCustomerGroupID IN ('CG01', 'CG02', 'CG03', 'CG04', 'CG05')
            AND pp.imiEndDate IS NULL
    )
    SELECT
        imiCustomerGroupID,
        CASE imiCustomerGroupID
            WHEN 'CG01' THEN 'LIST'
            WHEN 'CG02' THEN 'RACER'
            WHEN 'CG03' THEN 'JOBBER'
            WHEN 'CG04' THEN 'DIST'
            WHEN 'CG05' THEN 'WD'
            ELSE imiCustomerGroupID
        END AS price_label,
        imjUnitPrice AS retail_unit_price,
        imiPartPriceID,
        imiPartID,
        imiPartRevisionID,
        imiStartDate,
        imiEndDate,
        imiCreatedDate
    FROM priced
    WHERE row_number = 1
    ORDER BY
        CASE imiCustomerGroupID
            WHEN 'CG01' THEN 1
            WHEN 'CG02' THEN 2
            WHEN 'CG03' THEN 3
            WHEN 'CG04' THEN 4
            WHEN 'CG05' THEN 5
            ELSE 99
        END
    """
    try:
        return run_query(query, (part_id, revision_id or ""))
    except Exception:
        return pd.DataFrame()


def get_current_retail_price_legacy(part_id, revision_id="", *, run_query):
    query = """
    SELECT TOP 1
        pp.*,
        pb.*
    FROM PartPrices pp
    INNER JOIN PriceBreaks pb
        ON pb.imiPartPriceID = pp.impPartPriceID
    WHERE pp.impPartID = :param1
        AND COALESCE(pp.impPartRevisionID, '') = :param2
        AND pb.imiCustomerGroupID = 'CG01'
        AND pb.imiEndDate IS NULL
    ORDER BY pb.imiPartPriceID DESC
    """
    try:
        return run_query(query, (part_id, revision_id or ""))
    except Exception:
        return pd.DataFrame()


def add_retail_unit_price(rows):
    if rows.empty:
        return rows

    for column in (
        "imjUnitPrice",
        "imiUnitPrice",
        "imiPrice",
        "imiUnitSalePrice",
        "imiSellingPrice",
        "imiListPrice",
        "imiPriceBase",
    ):
        if column in rows.columns:
            rows = rows.copy()
            rows["retail_unit_price"] = rows[column]
            return rows
    return rows


def get_recent_jobs(part_id, revision_id="", limit=20, *, run_query):
    query = """
    SELECT TOP 20
        jmpJobID,
        jmpPartID,
        jmpPartRevisionID,
        jmpProductionQuantity,
        jmpQuantityCompleted,
        COALESCE(NULLIF(jmpQuantityCompleted, 0), jmpProductionQuantity) AS job_quantity,
        jmpCreatedDate,
        jmpClosedDate
    FROM Jobs
    WHERE jmpPartID = :param1
        AND COALESCE(jmpPartRevisionID, '') = :param2
        AND COALESCE(NULLIF(jmpQuantityCompleted, 0), jmpProductionQuantity) > 0
    ORDER BY
        COALESCE(jmpClosedDate, jmpCreatedDate) DESC,
        jmpJobID DESC
    """
    try:
        return run_query(query, (part_id, revision_id or ""))
    except Exception:
        return pd.DataFrame()


def get_operation_jobs(
    part_id, revision_id="", operation_sequence=0, limit=20, *, run_query
):
    query = """
    SELECT TOP 20
        j.jmpJobID,
        j.jmpPartID,
        j.jmpPartRevisionID,
        j.jmpProductionQuantity,
        j.jmpQuantityCompleted,
        COALESCE(NULLIF(j.jmpQuantityCompleted, 0), j.jmpProductionQuantity) AS job_quantity,
        j.jmpCreatedDate,
        j.jmpCompletedDate,
        j.jmpClosedDate,
        o.jmoJobAssemblyID,
        o.jmoJobOperationID,
        o.jmoWorkCenterID,
        o.jmoProcessID,
        o.jmoProcessShortDescription,
        o.jmoQuantityPerAssembly,
        o.jmoOperationQuantity,
        o.jmoQuantityComplete,
        o.jmoSetupHours,
        o.jmoProductionStandard,
        o.jmoEstimatedProductionHours,
        o.jmoCompletedSetupHours,
        o.jmoCompletedProductionHours,
        o.jmoActualSetupHours,
        o.jmoActualProductionHours,
        COALESCE(
            NULLIF(o.jmoQuantityComplete, 0),
            NULLIF(j.jmpQuantityCompleted, 0),
            NULLIF(o.jmoOperationQuantity, 0),
            j.jmpProductionQuantity
        ) AS operation_quantity,
        CASE
            WHEN COALESCE(
                NULLIF(o.jmoQuantityComplete, 0),
                NULLIF(j.jmpQuantityCompleted, 0),
                NULLIF(o.jmoOperationQuantity, 0),
                j.jmpProductionQuantity
            ) > 0
            THEN CAST(o.jmoActualProductionHours AS DECIMAL(19, 6)) / COALESCE(
                NULLIF(o.jmoQuantityComplete, 0),
                NULLIF(j.jmpQuantityCompleted, 0),
                NULLIF(o.jmoOperationQuantity, 0),
                j.jmpProductionQuantity
            )
            ELSE NULL
        END AS suggested_cycle_time_hours,
        COALESCE(
            NULLIF(o.jmoActualSetupHours, 0),
            NULLIF(o.jmoCompletedSetupHours, 0),
            o.jmoSetupHours
        ) AS suggested_setup_time_hours
    FROM Jobs j
    INNER JOIN JobOperations o ON o.jmoJobID = j.jmpJobID
    WHERE j.jmpPartID = :param1
        AND COALESCE(j.jmpPartRevisionID, '') = :param2
        AND o.jmoJobOperationID = :param3
        AND COALESCE(
            NULLIF(o.jmoQuantityComplete, 0),
            NULLIF(j.jmpQuantityCompleted, 0),
            NULLIF(o.jmoOperationQuantity, 0),
            j.jmpProductionQuantity
        ) > 0
    ORDER BY
        COALESCE(j.jmpClosedDate, j.jmpCompletedDate, j.jmpCreatedDate) DESC,
        j.jmpJobID DESC
    """
    return run_query(
        query, (part_id, revision_id or "", int(operation_sequence or 0))
    )


def search_parts(search_text, limit=12, *, run_query):
    query = """
    SELECT TOP 12
        imrPartID AS impPartID,
        imrPartRevisionID AS impPartRevisionID,
        imrShortDescription AS impShortDescription
    FROM PartRevisions
    WHERE imrPartID LIKE :param1
        AND COALESCE(imrInactive, 0) = 0
    ORDER BY imrPartID
    """
    return run_query(query, (f"{search_text}%",))

