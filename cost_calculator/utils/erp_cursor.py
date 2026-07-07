from urllib.parse import quote_plus

from sqlalchemy import create_engine


SERVER_NAME = "localhost\\MEZIEREDB22"
ERP_DATABASE = "M1_ME"
APP_DATABASE = "M2_ME"
UID = "cost_app_access"
PWD = "abc123"


def make_engine(database):
    odbc_str = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={SERVER_NAME};"
        f"DATABASE={database};"
        f"UID={UID};"
        f"PWD={PWD};"
        "TrustServerCertificate=yes;"
    )
    return create_engine(f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc_str)}")


erp_cnxn = make_engine(ERP_DATABASE)
app_cnxn = make_engine(APP_DATABASE)

# Backwards-compatible name for ERP reads. App-owned persistence must use app_cnxn.
cnxn = erp_cnxn
