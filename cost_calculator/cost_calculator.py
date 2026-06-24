from utils.queries import get_bom, get_operations
from utils.dataframes import empty_costing_dataframes
from costing.operations import build_operation_cost_lines

part_id = input("Imput part ID: ")

# bom_df = get_bom(part_id)
# ops_df = get_operations(part_id)

# dfs = empty_costing_dataframes()

print(build_operation_cost_lines(part_id, part_cost_id=1).to_string())