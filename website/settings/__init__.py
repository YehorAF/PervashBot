import dotenv
import os

dotenv.load_dotenv()

DBURL = os.getenv("DBURL")
DBNAME = os.getenv("DBNAME")
TOKEN = os.getenv("TOKEN")
BOTID = os.getenv("BOTID")
LIMIT = int(os.getenv("LIMIT"))