import os

import httpx
from dotenv import load_dotenv
from supabase import Client, ClientOptions, create_client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SECRET_KEY")

if not url or not key:
    raise RuntimeError(
        "SUPABASE_URL e SUPABASE_KEY (ou SUPABASE_SECRET_KEY) precisam estar definidas no .env."
    )

_http_client = httpx.Client(http2=False, timeout=120.0, follow_redirects=True)
supabase: Client = create_client(
    url,
    key,
    options=ClientOptions(httpx_client=_http_client),
)


def get_supabase() -> Client:
    return supabase
