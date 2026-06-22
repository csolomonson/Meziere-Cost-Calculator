import pyodbc

SERVER_NAME = 'localhost\\MEZIEREDB22'
DATABASE = 'M1_ME'
UID = 'cost_app_access'
PWD = 'abc123'

connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE};UID={UID};PWD={PWD};TrustServerCertificate=yes;"
cnxn = pyodbc.connect(connection_string)
cursor = cnxn.cursor()