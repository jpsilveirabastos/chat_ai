from os import getenv
from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv(raise_error_if_not_found=False))

os.environ['LANGSMITH_TRACING'] = getenv('LANGSMITH_TRACING')
os.environ['LANGSMITH_ENDPOINT'] = getenv('LANGSMITH_ENDPOINT')
os.environ['LANGSMITH_API_KEY'] = getenv('LANGSMITH_API_KEY')
os.environ['LANGSMITH_PROJECT'] = getenv('LANGSMITH_PROJECT')
os.environ['OPENAI_API_KEY'] = getenv('OPENAI_API_KEY')

DBNAME_PG = getenv('DBNAME_PG')
HOST_PG = getenv('HOST_PG')
USER_PG = getenv('USER_PG')
PASSWORD_PG = getenv('PASSWORD_PG')
AUTH_KEY = getenv('AUTH_KEY')
DB_URI = f'postgresql://{USER_PG}:{PASSWORD_PG}@{HOST_PG}:5432/{DBNAME_PG}'
TWILIO_SID = getenv('TWILIO_SID')
TWILIO_AUTH_TOKEN = getenv('TWILIO_AUTH_TOKEN')
GENAI_API_KEY = getenv('GENAI_API_KEY')