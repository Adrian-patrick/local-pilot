import os
import sys
from dotenv import load_dotenv
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.azure import AzureProvider

# Load configuration
load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

def create_model() -> OpenAIChatModel:
    """Configures the Azure OpenAI model."""
    provider = AzureProvider(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version=os.environ["AZURE_OPENAI_API_VERSION"],
    )
    return OpenAIChatModel(os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"], provider=provider)
