from os import getenv
from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv(raise_error_if_not_found=False))

os.environ['LANGSMITH_TRACING'] = getenv('LANGSMITH_TRACING')
os.environ['LANGSMITH_ENDPOINT'] = getenv('LANGSMITH_ENDPOINT')
os.environ['LANGSMITH_API_KEY'] = getenv('LANGSMITH_API_KEY')
os.environ['LANGSMITH_PROJECT'] = getenv('LANGSMITH_PROJECT')
os.environ['OPENAI_API_KEY'] = getenv('OPENAI_API_KEY')

AUTH_KEY = getenv('AUTH_KEY')
DB_URI = getenv('DB_URI')
GENAI_API_KEY = getenv('GENAI_API_KEY')
DEEPSEEK_API_KEY = getenv('DEEPSEEK_API_KEY')
ACCESS_TOKEN_CRM = getenv('ACCESS_TOKEN_CRM')
URL_CRM = getenv('URL_CRM')
ACCESS_TOKEN_CRM_FILE = getenv('ACCESS_TOKEN_CRM_FILE')