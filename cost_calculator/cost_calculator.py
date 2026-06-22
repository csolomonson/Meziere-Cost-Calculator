from utils.queries import get_bom, get_operations

part_id = input("Imput part ID: ")
print(get_bom(part_id))
print(get_operations(part_id))
