from langchain.sql_database import SQLDatabase
from .config import DBNAME_PG, HOST_PG, USER_PG, PASSWORD_PG

class PgConnection:

    def connect():
        db = SQLDatabase.from_uri(f'postgresql://{USER_PG}:{PASSWORD_PG}@{HOST_PG}:5432/{DBNAME_PG}')
        return db

