from utils.erp_cursor import cnxn
import pandas as pd
from sqlalchemy import text

def run_query(query, params = []):

    param_dict = {}
    for i in range(len(params)):
        param_dict[f'param{i+1}'] = params[i]

    return pd.read_sql(text(query), cnxn, params=param_dict)

def get_part(part_id):
    return run_query(f'SELECT * FROM Parts WHERE impPartID = :param1', (part_id))

def get_bom(part_id, revision_id=''):
    query = f'''
    SELECT immMethodID, immMethodRevisionID, immPartID, immPartRevisionID, immPartShortDescription, immQuantityPerAssembly, immEstimatedUnitCost
    FROM PartMaterials
    WHERE immMethodID = :param1 
        AND immMethodRevisionID = :param2 
        AND immBackflush = 1
    '''
    return run_query(query, (part_id, revision_id))

def get_operations(part_id, revision_id=''):
    query = f'''
    SELECT imoMethodID, imoMethodRevisionID, imoWorkCenterID, imoProcessID, imoProcessShortDescription, imoQuantityPerAssembly, imoSetupHours, imoProductionStandard, imoMethodOperationID, imoOperationType
    FROM PartOperations
    WHERE imoMethodID = :param1 
        AND imoMethodRevisionID = :param2
    '''
    return run_query(query, (part_id, revision_id))