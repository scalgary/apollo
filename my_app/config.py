import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent

# CSV paths
CSV_DIR = BASE_DIR /"data"
EVENTS_CSV = CSV_DIR / "events.csv"
USERS_CSV = CSV_DIR / "users.csv"
MEMBERSHIPS_CSV = CSV_DIR / "memberships.csv"

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./apollo.db")

# JWT
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

# Email
EMAIL_FROM = os.getenv("EMAIL_FROM", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
ADMIN_EMAIL_1 = os.getenv("ADMIN_EMAIL_1", "")
ADMIN_EMAIL_2 = os.getenv("ADMIN_EMAIL_2", "")


# Admin credentials
ADMIN_PASSWORD_1 = os.getenv("ADMIN_PASSWORD_1", "")
ADMIN_PASSWORD_2 = os.getenv("ADMIN_PASSWORD_2", "")