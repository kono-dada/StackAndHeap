from agents.extensions.models.litellm_model import LitellmModel
import dotenv
import os

dotenv.load_dotenv()
api_key = os.getenv("API_KEY") 
base_url = os.getenv("BASE_URL")
model_name = os.getenv("MODEL_NAME") or ''
assert model_name, "MODEL_NAME environment variable must be set."
model=LitellmModel(
    model=model_name,
    api_key=api_key,
    base_url=base_url
)