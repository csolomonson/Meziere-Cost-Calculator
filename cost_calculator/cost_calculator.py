import argparse

from costing.calculator import build_part_cost
from costing.persistence import save_costing_run


def parse_args():
    parser = argparse.ArgumentParser(description="Build a product cost calculation.")
    parser.add_argument("part_id", nargs="?", help="Part ID to cost")
    parser.add_argument("--revision", default="", help="Part revision to cost")
    parser.add_argument("--quantity", type=float, default=1, help="Quantity to cost")
    parser.add_argument("--costed-by", default=None, help="Name of the person costing this part")
    parser.add_argument("--notes", default=None, help="Notes to store with the costing run")
    parser.add_argument("--save", action="store_true", help="Save the costing run to SQL tables")
    return parser.parse_args()


def main():
    args = parse_args()
    part_id = args.part_id or input("Input part ID: ").strip()

    costing_run = build_part_cost(
        part_id=part_id,
        revision_id=args.revision,
        cost_quantity=args.quantity,
        costed_by=args.costed_by,
        notes=args.notes,
    )

    if args.save:
        part_cost_id = save_costing_run(costing_run)
        print(f"Saved PartCosts row {part_cost_id}")

    print("\nPart cost summary")
    print(costing_run["part_cost"].to_string(index=False))

    print("\nMaterial cost lines")
    print(costing_run["material_lines"].to_string(index=False))

    print("\nOperation cost lines")
    print(costing_run["operation_lines"].to_string(index=False))


if __name__ == "__main__":
    main()
