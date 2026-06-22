from sqlalchemy import create_engine
from urllib.parse import quote_plus

SERVER_NAME = 'localhost\\MEZIEREDB22'
DATABASE = 'M1_ME'
UID = 'cost_app_access'
PWD = 'abc123'

odbc_str = (f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={SERVER_NAME};"
            f"DATABASE={DATABASE};"
            f"UID={UID};"
            f"PWD={PWD};"
            f"TrustServerCertificate=yes;"
            )

cnxn = create_engine(f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc_str)}")
