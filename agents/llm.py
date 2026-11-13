import os
from dotenv import load_dotenv
import google.generativeai as genai


load_dotenv()  # Load environment variables from .env file

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
MODEL=os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
_model=genai.GenerativeModel(MODEL)


async def __llm(system:str,user:str,max_tokens:int=2000)-> str:
    """
    Generate a response from the LLM based on the system and user prompts.

    Args:
        system (str): The system prompt.
        user (str): The user prompt.
        max_tokens (int): Maximum number of tokens for the response.

    Returns:
        str: The generated response from the LLM.
    """

    prompt=f"System: {system}\nUser: {user}\n"
    response= await _model.generate_content_async(
        prompt,
        generation_config=genai.types.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=0.3,
        )
    )
    return response.text or ""