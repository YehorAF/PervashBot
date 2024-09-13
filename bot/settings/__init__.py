import dotenv
import os

DBURL = os.getenv("DBURL")
DBNAME = os.getenv("DBNAME")
REDIS = int(os.getenv("REDIS"))
TOKEN = os.getenv("TOKEN")
WEBSITE_URL = os.getenv("WEBSITE_URL")