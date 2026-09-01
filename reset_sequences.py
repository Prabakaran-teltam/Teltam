import os
import sys

# Ensure Django settings environment is initialized
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

import django
django.setup()

from django.db import connection
from django.apps import apps

def reset_all_db_sequences():
    """
    Synchronizes PostgreSQL auto-increment primary key sequences with MAX(id)
    across all database models to prevent primary key collision IntegrityError.
    """
    print("=== SYNCHRONIZING ALL POSTGRESQL PRIMARY KEY SEQUENCES ===")
    with connection.cursor() as cursor:
        # 1. Reset auth_user sequence specifically
        try:
            cursor.execute("SELECT setval(pg_get_serial_sequence('auth_user', 'id'), COALESCE(MAX(id), 1)) FROM auth_user;")
            auth_max = cursor.fetchone()[0]
            print(f"[OK] auth_user_id_seq synchronized to: {auth_max}")
        except Exception as e:
            print(f"[WARN] auth_user sequence sync: {e}")

        # 2. Reset sequences for all registered app models dynamically
        for model in apps.get_models():
            table_name = model._meta.db_table
            pk_name = model._meta.pk.name
            try:
                cursor.execute(f"SELECT setval(pg_get_serial_sequence('{table_name}', '{pk_name}'), COALESCE(MAX({pk_name}), 1)) FROM {table_name};")
                res = cursor.fetchone()
                if res and res[0] is not None:
                    print(f"  - Synchronized {table_name}.{pk_name} sequence to: {res[0]}")
            except Exception:
                pass

    print("\nAll database sequences have been synchronized successfully!")

if __name__ == '__main__':
    reset_all_db_sequences()
