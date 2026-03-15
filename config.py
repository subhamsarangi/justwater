import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
IMAGE_DIR = os.getenv("IMAGE_DIR", "static/images")
DATABASE_URL = os.getenv("DATABASE_URL")

WATERCOLOR_PROMPT = """Generate this as a traditional watercolor painting with the following qualities:
- Soft, translucent watercolor washes with visible paper grain showing through
- Loose ink or pencil linework as underdrawing visible beneath the color
- Bleeding, painterly edges — avoid sharp digital edges or gradients
- A limited, harmonious watercolor palette (avoid oversaturation)
- Natural white paper areas left unpainted for highlights

Subject to paint:
"""
