import math

import pandas as pd

from costing.common import markup_multiplier, number
from costing.operations import resolve_defaults_for_work_center
from utils.queries import get_bom, get_current_or_last_part_cost, get_default_costs, get_last_material_po, get_operations


get_last_part_cost = get_current_or_last_part_cost


MATERIAL_COST_COLUMNS = [
    "ucmPartMaterialLineID",
    "ucmPartCostID",
    "ucmCostQuantity",
    "ucmMaterialID",
    "ucmMaterialDescription",
    "ucmQtyPerAssembly",
    "ucmTotalQuantityRequired",
    "ucmIsPurchased",
    "ucmCostSource",
    "ucmManufacturedPartCostID",
    "ucmLastPO",
    "ucmLastPOCost",
    "ucmLastPODate",
    "ucmUnitCost",
    "ucmMinimumPurchaseQty",
    "ucmMaterialMarkup",
    "ucmWasteQuantity",
    "ucmRawCost",
    "ucmMarkedUpCost",
]


def resolve_material_purchase_cost(material):
    material_id = material.get("immPartID")
    material_revision_id = material.get("immPartRevisionID") or ""
    has_manufacturing_detail = (
        not get_bom(material_id, material_revision_id).empty
        or not get_operations(material_id, material_revision_id).empty
    )
    part_cost_df = get_last_part_cost(material_id, material_revision_id)

    if has_manufacturing_detail and not part_cost_df.empty:
        part_cost = part_cost_df.iloc[0]
        return {
            "is_purchased": False,
            "cost_source": "manufactured_history",
            "last_po": None,
            "last_po_cost": None,
            "last_po_date": part_cost.get("ucpDateCosted"),
            "unit_cost": number(part_cost.get("ucpUnitMarkedUpCost"), 0.0),
            "minimum_purchase_qty": 0.0,
            "material_markup": 1.0,
            "manufactured_part_cost_id": part_cost.get("ucpPartCostID"),
        }

    if has_manufacturing_detail:
        return {
            "is_purchased": False,
            "cost_source": "manufactured_route",
            "last_po": None,
            "last_po_cost": None,
            "last_po_date": None,
            "unit_cost": number(material.get("immEstimatedUnitCost"), 0.0),
            "minimum_purchase_qty": 0.0,
            "material_markup": 1.0,
        }

    po_df = get_last_material_po(material_id, material_revision_id)

    if not po_df.empty:
        po = po_df.iloc[0]
        po_date = po.get("pmlDueDate")
        if pd.isna(po_date):
            po_date = po.get("pmlCreatedDate")

        return {
            "is_purchased": True,
            "cost_source": "purchase_order",
            "last_po": f"{po.get('pmlPurchaseOrderID')}-{po.get('pmlPurchaseOrderLineID')}",
            "last_po_cost": number(po.get("pmlPurchaseUnitCostBase"), 0.0),
            "last_po_date": po_date,
            "unit_cost": number(po.get("pmlPurchaseUnitCostBase"), 0.0),
            "minimum_purchase_qty": 1.0,
            "material_markup": None,
        }

    if not part_cost_df.empty:
        part_cost = part_cost_df.iloc[0]
        return {
            "is_purchased": False,
            "cost_source": "manufactured_history",
            "last_po": None,
            "last_po_cost": None,
            "last_po_date": part_cost.get("ucpDateCosted"),
            "unit_cost": number(part_cost.get("ucpUnitMarkedUpCost"), 0.0),
            "minimum_purchase_qty": 0.0,
            "material_markup": 1.0,
            "manufactured_part_cost_id": part_cost.get("ucpPartCostID"),
        }

    return {
        "is_purchased": False,
        "cost_source": "erp_estimate",
        "last_po": None,
        "last_po_cost": None,
        "last_po_date": None,
        "unit_cost": number(material.get("immEstimatedUnitCost"), 0.0),
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

        rows.append({
            "ucmPartMaterialLineID": row_number + 1,
            "ucmPartCostID": part_cost_id,
            "ucmCostQuantity": cost_quantity,
            "ucmMaterialID": material.get("immPartID"),
            "ucmMaterialDescription": material.get("immPartShortDescription"),
            "ucmQtyPerAssembly": qty_per_assembly,
            "ucmTotalQuantityRequired": total_quantity,
            "ucmIsPurchased": purchase_cost["is_purchased"],
            "ucmLastPO": purchase_cost["last_po"],
            "ucmLastPOCost": purchase_cost["last_po_cost"],
            "ucmLastPODate": purchase_cost["last_po_date"],
            "ucmUnitCost": unit_cost,
            "ucmMinimumPurchaseQty": purchase_cost["minimum_purchase_qty"],
            "ucmMaterialMarkup": purchase_cost.get("material_markup") or material_markup,
            "ucmWasteQuantity": 0.0,
            "ucmCostSource": purchase_cost.get("cost_source"),
            "ucmManufacturedPartCostID": purchase_cost.get("manufactured_part_cost_id"),
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
        is_purchased = bool(line.get("ucmIsPurchased"))
        purchase_increment = number(line.get("ucmMinimumPurchaseQty"), 0.0) if is_purchased else 0.0
        if purchase_increment > 0 and total_quantity > 0:
            quantity_to_cost = math.ceil(total_quantity / purchase_increment) * purchase_increment
        else:
            quantity_to_cost = total_quantity
        waste_quantity = max(quantity_to_cost - total_quantity, 0.0)
        raw_cost = quantity_to_cost * number(line.get("ucmUnitCost"), 0.0)
        marked_up_cost = raw_cost * markup_multiplier(line.get("ucmMaterialMarkup"))

        material_lines_df.at[n, "ucmWasteQuantity"] = waste_quantity
        material_lines_df.at[n, "ucmRawCost"] = raw_cost
        material_lines_df.at[n, "ucmMarkedUpCost"] = marked_up_cost

    return material_lines_df
