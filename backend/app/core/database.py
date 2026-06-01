from supabase import Client, create_client

from app.core.config import get_env

supabase: Client = create_client(
    get_env("SUPABASE_URL"),
    get_env("SUPABASE_KEY"),
)
