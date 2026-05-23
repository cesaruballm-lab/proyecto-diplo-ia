import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Cargar variables de entorno
load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    raise RuntimeError("Las variables de entorno SUPABASE_URL y/o SUPABASE_KEY no están definidas.")

# Cliente oficial de Supabase
supabase: Client = create_client(supabase_url, supabase_key)
