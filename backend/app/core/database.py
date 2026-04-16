from dotenv import load_dotenv
from supabase import Client, create_client
import os

load_dotenv()

supabase: Client = create_client(
    os.environ.get("SUPABASE_URL"),
    os.environ.get("SUPABASE_KEY"),
)