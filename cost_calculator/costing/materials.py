import math

import pandas as pd

from costing.common import markup_multiplier, number
from costing.operations import resolve_defaults_for_work_center
from utils.queries import get_bom, get_current_or_last_part_cost, get_current_retail_price, get_default_costs, get_last_material_po, get_operations


get_last_part_cost = get_current_or_last_part_cost


MATERIAL_COST_COLUMNS = [
    "ucmPartMaterialLineID",
    "ucmPartCostID",
    "ucmCostQuantity",
    "ucmMaterialID",
    "ucmMaterialDescription",
    "ucmQtyPerAssembly",
    "ucmTotalQuantityRequired",
    "ucmBackflush",
    "ucmIsPurchased",
    "ucmCostSource",
    "ucmHasManufacturingDetail",
    "ucmManufacturingMaterialCount",
    "ucmManufacturingOperationCount",
    "ucmManufacturedPartCostID",
    "ucmManufacturedPartCostIsCurrent",
    "ucmLastPO",
    "ucmLastPOCost",
    "ucmLastPODate",
    "ucmRetailUnitPrice",
    "ucmUnitCost",
    "ucmPurchaseUnitCost",
    "ucmMaterialPriceMode",
    "ucmLastPOPurchaseUnitCost",
    "ucmLastPOConversionFactor",
    "ucmLastPOPurchaseUnit",
    "ucmLastPOInventoryUnit",
    "ucmMinimumPurchaseQty",
    "ucmMaterialMarkup",
    "ucmWasteQuantity",
    "ucmMaterialsRawCost",
    "ucmMaterialsMarkedUpCost",
    "ucmMachineTimeRawCost",
    "ucmMachineTimeMarkedUpCost",
    "ucmLaborRawCost",
    "ucmLaborMarkedUpCost",
    "ucmExternalOperationsRawCost",
    "ucmExternalOperationsMarkedUpCost",
    "ucmAdditionalRawCost",
    "ucmAdditionalMarkedUpCost",
    "ucmRawCost",
    "ucmMarkedUpCost",
]


COST_BUCKETS = [
    ("materials", "ucmMaterialsRawCost", "ucmMaterialsMarkedUpCost", "ucpMaterialsRawCost"),
    ("machine", "ucmMachineTimeRawCost", "ucmMachineTimeMarkedUpCost", "ucpMachineTimeRawCost"),
    ("labor", "ucmLaborRawCost", "ucmLaborMarkedUpCost", "ucpLaborRawCost"),
    ("external", "ucmExternalOperationsRawCost", "ucmExternalOperationsMarkedUpCost", "ucpExternalOperationsRawCost"),
    ("additional", "ucmAdditionalRawCost", "ucmAdditionalMarkedUpCost", "ucpAdditionalRawCost"),
]


def po_unit(po, *names):
    for name in names:
        value = po.get(name)
        if value is not None and not pd.isna(value) and value != "":
            return value
    return None


def flag_value(value, default=False):
    if value is None or pd.isna(value):
        return default
    if isinstance(value, str):
        return value.strip().lower() not in ("", "0", "false", "no", "n")
    return bool(value)


def child_cost_breakdown(part_cost):
    unit_raw_cost = number(part_cost.get("ucpUnitRawCost"), 0.0)
    child_quantity = number(part_cost.get("ucpCostQuantity"), 0.0) or 1.0
    breakdown = {}
    for key, _, _, part_field in COST_BUCKETS:
        breakdown[key] = number(part_cost.get(part_field), 0.0) / child_quantity
    if not any(breakdown.values()):
        breakdown["materials"] = unit_raw_cost
    return breakdown


def resolve_material_purchase_cost(material):
    material_id = material.get("immPartID")
    material_revision_id = material.get("immPartRevisionID") or ""
    bom_df = get_bom(material_id, material_revision_id)
    operations_df = get_operations(material_id, material_revision_id)
    material_count = len(bom_df)
    operation_count = len(operations_df)
    has_manufacturing_detail = material_count > 0 or operation_count > 0
    part_cost_df = get_last_part_cost(material_id, material_revision_id)
    retail_df = get_current_retail_price(material_id, material_revision_id)
    retail_price = None if retail_df.empty else retail_df.iloc[0].get("retail_unit_price")
    route_status = {
        "has_manufacturing_detail": has_manufacturing_detail,
        "manufacturing_material_count": material_count,
        "manufacturing_operation_count": operation_count,
    }

    if has_manufacturing_detail and not part_cost_df.empty:
        part_cost = part_cost_df.iloc[0]
        return {
            **route_status,
            "is_purchased": False,
            "cost_source": "manufactured_history",
            "last_po": None,
            "last_po_cost": None,
            "last_po_date": part_cost.get("ucpDateCosted"),
            "unit_cost": number(part_cost.get("ucpUnitRawCost"), 0.0),
            "cost_breakdown": child_cost_breakdown(part_cost),
            "retail_unit_price": retail_price,
            "minimum_purchase_qty": 0.0,
            "material_markup": None,
            "manufactured_part_cost_id": part_cost.get("ucpPartCostID"),
            "manufactured_part_cost_is_current": bool(part_cost.get("ucpIsCurrent")),
        }

    if has_manufacturing_detail:
        return {
            **route_status,
            "is_purchased": False,
            "cost_source": "manufactured_route",
            "last_po": None,
            "last_po_cost": None,
            "last_po_date": None,
            "unit_cost": number(material.get("immEstimatedUnitCost"), 0.0),
            "retail_unit_price": retail_price,
            "minimum_purchase_qty": 0.0,
            "material_markup": None,
        }

    po_df = get_last_material_po(material_id, material_revision_id)

    if not po_df.empty:
        po = po_df.iloc[0]
        po_date = po.get("pmlDueDate")
        if pd.isna(po_date):
            po_date = po.get("pmlCreatedDate")

        return {
            **route_status,
            "is_purchased": True,
            "cost_source": "purchase_order",
            "last_po": f"{po.get('pmlPurchaseOrderID')}-{po.get('pmlPurchaseOrderLineID')}",
            "last_po_cost": number(po.get("pmlInventoryUnitCostBase"), number(po.get("pmlPurchaseUnitCostBase"), 0.0)),
            "last_po_date": po_date,
            "unit_cost": number(po.get("pmlInventoryUnitCostBase"), number(po.get("pmlPurchaseUnitCostBase"), 0.0)),
            "purchase_unit_cost": number(po.get("pmlPurchaseUnitCostBase"), 0.0),
            "material_price_mode": "purchase",
            "last_po_purchase_unit_cost": number(po.get("pmlPurchaseUnitCostBase"), 0.0),
            "last_po_conversion_factor": number(po.get("pmlConversionFactor"), 1.0),
            "last_po_purchase_unit": po_unit(po, "pmlPurchaseUnitOfMeasure", "pmlPurchaseUnitOfMeasureID", "pmlPurchaseUOM", "pmlPurchaseUM"),
            "last_po_inventory_unit": po_unit(po, "pmlInventoryUnitOfMeasure", "pmlInventoryUnitOfMeasureID", "pmlInventoryUOM", "pmlInventoryUM"),
            "retail_unit_price": retail_price,
            "minimum_purchase_qty": 1.0,
            "material_markup": None,
        }

    if not part_cost_df.empty:
        part_cost = part_cost_df.iloc[0]
        return {
            **route_status,
            "is_purchased": False,
            "cost_source": "manufactured_history",
            "last_po": None,
            "last_po_cost": None,
            "last_po_date": part_cost.get("ucpDateCosted"),
            "unit_cost": number(part_cost.get("ucpUnitRawCost"), 0.0),
            "cost_breakdown": child_cost_breakdown(part_cost),
            "retail_unit_price": retail_price,
            "minimum_purchase_qty": 0.0,
            "material_markup": None,
            "manufactured_part_cost_id": part_cost.get("ucpPartCostID"),
            "manufactured_part_cost_is_current": bool(part_cost.get("ucpIsCurrent")),
        }

    return {
        **route_status,
        "is_purchased": False,
        "cost_source": "erp_estimate",
        "last_po": None,
        "last_po_cost": None,
        "last_po_date": None,
        "unit_cost": number(material.get("immEstimatedUnitCost"), 0.0),
        "retail_unit_price": retail_price,
        "minimum_purchase_qty": 0.0,
        "material_markup": None,
    }


def build_material_cost_lines(
    part_id,
    revision_id="",
    part_cost_id=None,
    cost_quantity=1,
):
    bom_df = get_bom(part_id, revision_id)
    defaults_df = get_default_costs()

    if bom_df.empty:
        return pd.DataFrame(columns=MATERIAL_COST_COLUMNS)

    defaults = resolve_defaults_for_work_center(
        defaults_df=defaults_df,
        work_center_id="__GLOBAL__",
        cost_quantity=cost_quantity,
    )
    material_markup = markup_multiplier(defaults.get("ucdDefaultMaterialMarkup"))

    rows = []
    for row_number, material in bom_df.reset_index(drop=True).iterrows():
        qty_per_assembly = number(material.get("immQuantityPerAssembly"), 0.0)
        total_quantity = qty_per_assembly * cost_quantity
        purchase_cost = resolve_material_purchase_cost(material)
        unit_cost = purchase_cost["unit_cost"]

        split_totals = {
            raw_column: total_quantity * number(purchase_cost.get("cost_breakdown", {}).get(key), 0.0)
            for key, raw_column, _, _ in COST_BUCKETS
        }

        rows.append({
            "ucmPartMaterialLineID": row_number + 1,
            "ucmPartCostID": part_cost_id,
            "ucmCostQuantity": cost_quantity,
            "ucmMaterialID": material.get("immPartID"),
            "ucmMaterialDescription": material.get("immPartShortDescription"),
            "ucmQtyPerAssembly": qty_per_assembly,
            "ucmTotalQuantityRequired": total_quantity,
            "ucmBackflush": flag_value(material.get("immBackflush")),
            "ucmIsPurchased": purchase_cost["is_purchased"],
            "ucmHasManufacturingDetail": purchase_cost.get("has_manufacturing_detail"),
            "ucmManufacturingMaterialCount": purchase_cost.get("manufacturing_material_count"),
            "ucmManufacturingOperationCount": purchase_cost.get("manufacturing_operation_count"),
            "ucmLastPO": purchase_cost["last_po"],
            "ucmLastPOCost": purchase_cost["last_po_cost"],
            "ucmLastPODate": purchase_cost["last_po_date"],
            "ucmRetailUnitPrice": purchase_cost.get("retail_unit_price"),
            "ucmUnitCost": unit_cost,
            "ucmPurchaseUnitCost": purchase_cost.get("purchase_unit_cost"),
            "ucmMaterialPriceMode": purchase_cost.get("material_price_mode"),
            "ucmLastPOPurchaseUnitCost": purchase_cost.get("last_po_purchase_unit_cost"),
            "ucmLastPOConversionFactor": purchase_cost.get("last_po_conversion_factor"),
            "ucmLastPOPurchaseUnit": purchase_cost.get("last_po_purchase_unit"),
            "ucmLastPOInventoryUnit": purchase_cost.get("last_po_inventory_unit"),
            "ucmMinimumPurchaseQty": purchase_cost["minimum_purchase_qty"],
            "ucmMaterialMarkup": purchase_cost.get("material_markup") or material_markup,
            "ucmWasteQuantity": 0.0,
            "ucmMaterialsRawCost": 0.0,
            "ucmMaterialsMarkedUpCost": 0.0,
            "ucmMachineTimeRawCost": 0.0,
            "ucmMachineTimeMarkedUpCost": 0.0,
            "ucmLaborRawCost": 0.0,
            "ucmLaborMarkedUpCost": 0.0,
            "ucmExternalOperationsRawCost": 0.0,
            "ucmExternalOperationsMarkedUpCost": 0.0,
            "ucmAdditionalRawCost": 0.0,
            "ucmAdditionalMarkedUpCost": 0.0,
            "ucmCostSource": purchase_cost.get("cost_source"),
            "ucmManufacturedPartCostID": purchase_cost.get("manufactured_part_cost_id"),
            "ucmManufacturedPartCostIsCurrent": purchase_cost.get("manufactured_part_cost_is_current"),
            **split_totals,
            "ucmRawCost": 0.0,
            "ucmMarkedUpCost": 0.0,
        })

    return update_material_costs(pd.DataFrame(rows, columns=MATERIAL_COST_COLUMNS))


def update_material_costs(material_lines_df):
    material_lines_df = material_lines_df.copy()

    if material_lines_df.empty:
        return material_lines_df

    for n, line in material_lines_df.iterrows():
        total_quantity = number(line.get("ucmTotalQuantityRequired"), 0.0)
        is_backflushed = flag_value(line.get("ucmBackflush"), default=True)
        is_purchased = flag_value(line.get("ucmIsPurchased"))
        purchase_increment = number(line.get("ucmMinimumPurchaseQty"), 0.0) if is_purchased else 0.0
        if purchase_increment > 0 and total_quantity > 0:
            quantity_to_cost = math.ceil(total_quantity / purchase_increment) * purchase_increment
        else:
            quantity_to_cost = total_quantity
        waste_quantity = max(quantity_to_cost - total_quantity, 0.0)
        if not is_backflushed:
            material_lines_df.at[n, "ucmWasteQuantity"] = 0.0
            material_lines_df.at[n, "ucmRawCost"] = 0.0
            material_lines_df.at[n, "ucmMarkedUpCost"] = 0.0
            for _, raw_column, marked_column, _ in COST_BUCKETS:
                material_lines_df.at[n, raw_column] = 0.0
                material_lines_df.at[n, marked_column] = 0.0
            continue
        previous_quantity = number(line.get("ucmCostQuantity"), 0.0)
        previous_required = number(line.get("ucmQtyPerAssembly"), 0.0) * previous_quantity
        if purchase_increment > 0 and previous_required > 0:
            previous_quantity_to_cost = math.ceil(previous_required / purchase_increment) * purchase_increment
        else:
            previous_quantity_to_cost = previous_required
        previous_quantity_to_cost = previous_quantity_to_cost or 1.0
        if is_purchased or line.get("ucmCostSource") == "purchase_order":
            unit_breakdown = {raw_column: 0.0 for _, raw_column, _, _ in COST_BUCKETS}
            unit_breakdown["ucmMaterialsRawCost"] = number(line.get("ucmUnitCost"), 0.0)
        else:
            unit_breakdown = {
                raw_column: number(line.get(raw_column), 0.0) / previous_quantity_to_cost
                for _, raw_column, _, _ in COST_BUCKETS
            }
        if not any(unit_breakdown.values()):
            unit_breakdown["ucmMaterialsRawCost"] = number(line.get("ucmUnitCost"), 0.0)
        raw_cost = 0.0
        marked_up_cost = 0.0
        for _, raw_column, marked_column, _ in COST_BUCKETS:
            bucket_raw = quantity_to_cost * unit_breakdown[raw_column]
            bucket_marked = bucket_raw * markup_multiplier(line.get("ucmMaterialMarkup"))
            raw_cost += bucket_raw
            marked_up_cost += bucket_marked
            material_lines_df.at[n, raw_column] = bucket_raw
            material_lines_df.at[n, marked_column] = bucket_marked

        material_lines_df.at[n, "ucmWasteQuantity"] = waste_quantity
        material_lines_df.at[n, "ucmRawCost"] = raw_cost
        material_lines_df.at[n, "ucmMarkedUpCost"] = marked_up_cost

    return material_lines_df
