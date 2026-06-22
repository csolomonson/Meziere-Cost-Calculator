from utils.erp_cursor import cursor

def run_query(cursor, query):
    cursor.execute(query)
    return cursor.fetchall()

def get_part(part_id):
    return run_query(cursor, f'SELECT * FROM Parts WHERE impPartID = \'{part_id}\'')

def get_bom(part_id):
    query = f'''
    SELECT immPartID, immPartRevisionID, immPartShortDescription, immQuantityPerAssembly, immEstimatedUnitCost
    FROM PartMaterials
    WHERE immMethodID = '{part_id}' AND immBackflush = 1
    '''
    return run_query(cursor, query)