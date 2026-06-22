from utils.erp_cursor import cursor

def run_query(cursor, query):
    cursor.execute(query)
    return cursor.fetchall()

def get_part(part_id):
    return run_query(cursor, f'SELECT * FROM Parts WHERE impPartID = \'{part_id}\'')