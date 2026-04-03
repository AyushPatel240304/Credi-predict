import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    """Create and return a database connection"""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', 5432),
            database=os.getenv('DB_NAME', 'credipredict_db'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD')
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def create_tables():
    """Create all tables if they don't exist"""
    conn = get_connection()
    if not conn:
        print("Failed to connect to database")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Table 1 - Individual Predictions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS individual_predictions (
                id SERIAL PRIMARY KEY,
                code_gender VARCHAR(1),
                flag_own_car VARCHAR(1),
                flag_own_realty VARCHAR(1),
                cnt_children INTEGER,
                amt_income_total FLOAT,
                name_income_type VARCHAR(50),
                name_education_type VARCHAR(50),
                name_family_status VARCHAR(50),
                name_housing_type VARCHAR(50),
                cnt_fam_members INTEGER,
                occupation_type VARCHAR(50),
                age_years INTEGER,
                employed_years INTEGER,
                risk_probability FLOAT,
                risk_level VARCHAR(20),
                decision VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Table 2 - Batch Jobs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS batch_jobs (
                id SERIAL PRIMARY KEY,
                total_records INTEGER,
                approved_count INTEGER,
                rejected_count INTEGER,
                review_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Table 3 - Batch Predictions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS batch_predictions (
                id SERIAL PRIMARY KEY,
                batch_job_id INTEGER REFERENCES batch_jobs(id),
                code_gender VARCHAR(1),
                flag_own_car VARCHAR(1),
                flag_own_realty VARCHAR(1),
                cnt_children INTEGER,
                amt_income_total FLOAT,
                name_income_type VARCHAR(50),
                name_education_type VARCHAR(50),
                name_family_status VARCHAR(50),
                name_housing_type VARCHAR(50),
                cnt_fam_members INTEGER,
                occupation_type VARCHAR(50),
                age_years INTEGER,
                employed_years INTEGER,
                risk_probability FLOAT,
                risk_level VARCHAR(20),
                decision VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Table 4 - Tickets
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id SERIAL PRIMARY KEY,
                ticket_id VARCHAR(20) UNIQUE NOT NULL,
                email VARCHAR(100) NOT NULL,
                subject VARCHAR(200) NOT NULL,
                description TEXT NOT NULL,
                status VARCHAR(20) DEFAULT 'Open',
                admin_reply TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Table 5 - Ticket Rate Limit
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ticket_rate_limit (
                id SERIAL PRIMARY KEY,
                email VARCHAR(100) NOT NULL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Table 6 - FAQs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS faqs (
                id SERIAL PRIMARY KEY,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                display_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        print("All tables created successfully!")
        return True
        
    except Exception as e:
        print(f"Error creating tables: {e}")
        conn.rollback()
        conn.close()
        return False

if __name__ == "__main__":
    print("Setting up CrediPredict database...")
    if create_tables():
        print("Database setup complete!")
    else:
        print("Database setup failed!")