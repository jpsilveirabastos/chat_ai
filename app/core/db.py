from langchain_community.utilities import SQLDatabase
from .config import DB_URI

class PgConnection:

    def connect():
        db = SQLDatabase.from_uri(DB_URI)
        return db

