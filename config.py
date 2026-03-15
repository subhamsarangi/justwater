import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
IMAGE_DIR = os.getenv("IMAGE_DIR", "static/images")
DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
OWNER_EMAIL = os.getenv("OWNER_EMAIL", "")
TOKEN_LIMIT = int(os.getenv("TOKEN_LIMIT", "1000000"))

WATERCOLOR_PROMPT = """Generate this as a traditional watercolor painting with the following qualities:
- Soft, translucent watercolor washes with visible paper grain showing through
- Loose ink or pencil linework as underdrawing visible beneath the color
- Bleeding, painterly edges — avoid sharp digital edges or gradients
- A limited, harmonious watercolor palette (avoid oversaturation)
- Natural white paper areas left unpainted for highlights

Subject to paint:
"""
