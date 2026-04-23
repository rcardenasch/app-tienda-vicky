# 📁 ESTRUCTURA RECOMENDADA
# ├── app.py
# ├── models.py
# ├── config.py
# └── requirements.txt

# =========================
# config.py
# =========================
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = 'super-secret-key'

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:1234@localhost:5432/App_Tienda" # ingresa parametros de acceso a bd local
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static/uploads")

    SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_pre_ping": True,
}