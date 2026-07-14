from urllib.parse import quote_plus

from sqlalchemy import create_engine

from app_config import boolean_setting, secret_setting, setting


SERVER_NAME = setting("COST_DB_SERVER", "localhost\\MEZIEREDB22")
ERP_DATABASE = setting("COST_ERP_DATABASE", "M1_ME")
APP_DATABASE = setting("COST_APP_DATABASE", "M2_ME")
UID = setting("COST_DB_USERNAME", "cost_app_access")
PWD = secret_setting("COST_DB_PASSWORD", "db_password.txt", "")
ODBC_DRIVER = setting("COST_DB_DRIVER", "ODBC Driver 17 for SQL Server")
# The existing local SQL instance uses its own certificate. Containers override
# this to false by default so production must establish certificate trust.
TRUST_SERVER_CERTIFICATE = boolean_setting("COST_DB_TRUST_SERVER_CERTIFICATE", True)


def make_engine(database):
    odbc_str = (
        f"DRIVER={{{ODBC_DRIVER}}};"
        f"SERVER={SERVER_NAME};"
        f"DATABASE={database};"
        f"UID={UID};"
        f"PWD={PWD};"
        "Encrypt=yes;"
        f"TrustServerCertificate={'yes' if TRUST_SERVER_CERTIFICATE else 'no'};"
    )
    return create_engine(f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc_str)}")


erp_cnxn = make_engine(ERP_DATABASE)
app_cnxn = make_engine(APP_DATABASE)

# Backwards-compatible name for ERP reads. App-owned persistence must use app_cnxn.
cnxn = erp_cnxn
