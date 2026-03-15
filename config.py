import os
from dotenv import load_dotenv

load_dotenv()

ENV = os.getenv("ENV", "local")
IS_LOCAL = ENV == "local"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
IMAGE_DIR = os.getenv("IMAGE_DIR", "")  # local
DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY", "")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
OWNER_EMAIL = os.getenv("OWNER_EMAIL", "")
TOKEN_LIMIT = int(os.getenv("TOKEN_LIMIT", "20000"))

R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL")

WATERCOLOR_PROMPT = """Generate this as a traditional watercolor painting with the following qualities:
- Soft, translucent watercolor washes with visible paper grain showing through
- Loose ink or pencil linework as underdrawing visible beneath the color
- Bleeding, painterly edges — avoid sharp digital edges or gradients
- A limited, harmonious watercolor palette (avoid oversaturation)
- Natural white paper areas left unpainted for highlights

Subject to paint:
"""

INK_WASH_PROMPT = """Generate this as an ink wash painting inspired by sumi-e technique, with the following qualities:
- Monochromatic — black ink with layered grey washes, no color
- Minimal, expressive brushwork — every stroke intentional, nothing overworked
- Generous empty white space used as a compositional element, not a void
- Soft ink bleeds and diffused edges where ink meets wet paper
- Subjects rendered through gesture and form, not fine detail
- No text, no Chinese or Japanese characters, no calligraphy, no seals or stamps of any kind

Subject to paint:
"""
