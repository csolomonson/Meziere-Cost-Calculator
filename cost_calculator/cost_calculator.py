from utils.erp_cursor import cursor

part_id = input("Imput part ID: ")
cursor.execute(f'SELECT * FROM Parts WHERE impPartID = \'{part_id}\'')
rows = cursor.fetchall()

print(rows)