import os
import sys
from sqlalchemy import create_engine, text

# Adjust path to import app modules
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.core.config import settings

def test_connection():
    print("Checking connection settings...")
    print(f"Host: {settings.MYSQL_HOST}")
    print(f"Port: {settings.MYSQL_PORT}")
    print(f"User: {settings.MYSQL_USER}")
    print(f"Database: {settings.MYSQL_DATABASE}")
    print(f"SSL CA Path: {settings.MYSQL_SSL_CA}")
    
    url = settings.database_url
    print(f"Database URL: {url.render_as_string(hide_password=True)}")
    
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print(f"Connection successful! Result of SELECT 1: {result.scalar()}")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    test_connection()
