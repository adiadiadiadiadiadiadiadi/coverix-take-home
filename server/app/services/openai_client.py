from openai import OpenAI
import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

raw_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=raw_key)