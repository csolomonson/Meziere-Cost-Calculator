from utils.erp_cursor import cnxn
import pandas as pd

def run_query(query):

    return pd.read_sql(query, cnxn)

def get_part(part_id):
    return run_query(f'SELECT * FROM Parts WHERE impPartID = \'{part_id}\'')

def get_bom(part_id, revision_id=''):
    query = f'''
    SELECT immMethodID, immPartID, immPartRevisionID, immPartShortDescription, immQuantityPerAssembly, immEstimatedUnitCost
    FROM PartMaterials
    WHERE immMethodID = '{part_id}' AND immMethodRevisionID = '{revision_id}' AND immBackflush = 1
    '''
    return run_query(query)

def get_operations(part_id, revision_id=''):
    query = f'''
    SELECT imoWorkCenterID, imoProcessID, imoProcessShortDescription, imoQuantityPerAssembly, imoSetupHours, imoProductionStandard
    FROM PartOperations
    WHERE imoMethodID = '{part_id}' AND imoMethodRevisionID = '{revision_id}'
    '''
    return run_query(query)