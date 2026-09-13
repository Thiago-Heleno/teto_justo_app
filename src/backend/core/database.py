import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    raise RuntimeError(
        "SUPABASE_URL e SUPABASE_KEY precisam estar definidas no .env."
    )

supabase: Client = create_client(url, key)


def get_supabase() -> Client:
    return supabase
