"""
Run this script once to add the admin_login_attempts table
"""
from database import get_connection

def migrate():
    conn = get_connection()
    if not conn:
        print("DB connection failed")
        return
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_login_attempts (
            id SERIAL PRIMARY KEY,
            ip_address VARCHAR(50) NOT NULL,
            success BOOLEAN DEFAULT FALSE,
            attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()
    print("Migration complete — admin_login_attempts table created")

if __name__ == "__main__":
    migrate()