"""
LLM Handler module - Communication with Google's Gemini API.
Formats requests and handles responses from the model.
"""

import os
import logging
import time
from typing import Optional, Dict, Any
from dotenv import load_dotenv

import google.generativeai as genai

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class LLMHandler:
    """
    Handles all communication with Google Gemini models.
    """
    
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_API_KEY')
        # Default Gemini model; adjust via env var LLM_MODEL
        self.model = os.getenv('LLM_MODEL', 'gemini-1.5-flash')
        self.max_tokens = int(os.getenv('MAX_TOKENS', '800'))
        self.temperature = float(os.getenv('TEMPERATURE', '0.7'))
        self.max_retries = int(os.getenv('MAX_RETRIES', '3'))
        self.retry_delay = int(os.getenv('RETRY_DELAY', '1'))

        if not self.api_key:
            logger.warning("No GOOGLE_API_KEY found in environment variables")
        else:
            try:
                genai.configure(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to configure Google Generative AI client: {e}")

    def call_llm(self, prompt: str, system_message: Optional[str] = None) -> str:
        """
        Make a call to the Gemini model with the given prompt.
        """
        if not self.api_key:
            logger.error("Cannot call LLM: No GOOGLE_API_KEY configured")
            raise ValueError("Gemini API key not configured")

        # Optionally truncate prompt to keep within budget
        prompt_to_send = self.truncate_prompt(prompt, max_context_tokens=3000)

        generation_config = {
            "temperature": self.temperature,
            "max_output_tokens": self.max_tokens,
        }

        for attempt in range(self.max_retries):
            try:
                logger.info(f"Making LLM API call (attempt {attempt + 1})")

                if system_message:
                    model = genai.GenerativeModel(
                        model_name=self.model,
                        system_instruction=system_message,
                        generation_config=generation_config,
                    )
                else:
                    model = genai.GenerativeModel(
                        model_name=self.model,
                        generation_config=generation_config,
                    )

                response = model.generate_content(prompt_to_send)

                # Prefer .text; fallback to candidates
                result_text = getattr(response, 'text', None)
                if not result_text and getattr(response, 'candidates', None):
                    try:
                        result_text = response.candidates[0].content.parts[0].text
                    except Exception:
                        result_text = ""

                result_text = (result_text or "").strip()
                logger.info("LLM API call successful")
                return result_text

            except Exception as e:
                logger.error(f"Error calling Gemini (attempt {attempt + 1}): {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))
                else:
                    raise

        raise Exception("Max retries exceeded for LLM API call")

    def call_llm_with_context(self, prompt: str, context: Dict[str, Any]) -> str:
        system_message = self._build_system_message(context)
        return self.call_llm(prompt, system_message)

    def _build_system_message(self, context: Dict[str, Any]) -> str:
        base_message = """You are an expert data analyst and Python programmer. 
        You help users analyze data by writing precise, executable Python code.
        
        Guidelines:
        1. Write clean, well-commented Python code
        2. Include all necessary imports
        3. Handle errors gracefully
        4. Provide clear, actionable insights
        5. Focus on answering the specific questions asked
        """

        if context.get('data_type'):
            base_message += f"\n\nData type: {context['data_type']}"

        if context.get('data_structure'):
            base_message += f"\nData structure: {context['data_structure']}"

        if context.get('previous_error'):
            base_message += f"\n\nPrevious error encountered: {context['previous_error']}"
            base_message += "\nPlease fix the error and ensure the code runs successfully."

        return base_message

    def validate_api_key(self) -> bool:
        if not self.api_key:
            return False
        try:
            model = genai.GenerativeModel(model_name=self.model)
            resp = model.generate_content("Say 'working' if API key is valid.")
            text = getattr(resp, 'text', '') or ''
            return 'working' in text.lower()
        except Exception as e:
            logger.error(f"API key validation failed: {str(e)}")
            return False

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "max_retries": self.max_retries,
            "api_key_configured": bool(self.api_key),
            "provider": "google-generativeai",
            "api_key_valid": self.validate_api_key() if self.api_key else False,
        }

    def estimate_tokens(self, text: str) -> int:
        # Rough estimation: 1 token ≈ 4 characters
        return len(text) // 4

    def truncate_prompt(self, prompt: str, max_context_tokens: int = 3000) -> str:
        estimated_tokens = self.estimate_tokens(prompt)
        if estimated_tokens <= max_context_tokens:
            return prompt
        target_length = max_context_tokens * 4
        if len(prompt) <= target_length:
            return prompt
        keep_start = target_length // 2
        keep_end = target_length // 2
        truncated = (prompt[:keep_start] +
                     "\n\n... [TRUNCATED FOR LENGTH] ...\n\n" +
                     prompt[-keep_end:])
        logger.warning(f"Prompt truncated from {len(prompt)} to {len(truncated)} characters")
        return truncated