import json
import time
import asyncio
from groq import Groq
from config import settings
from app.logger import get_logger

logger = get_logger(__name__)


class GroqService:
    """Simple Groq API wrapper"""

    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL
        self.timeout = settings.GROQ_TIMEOUT
        self.max_tokens = settings.GROQ_MAX_TOKENS
        self.temperature = settings.GROQ_TEMPERATURE

    async def call(self, prompt: str, temperature: float = None, max_tokens: int = None) -> str:
        """
        Call Groq API asynchronously.
        Uses thread pool executor to run sync Groq client.
        """
        try:
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    self._call_sync,
                    prompt,
                    temperature or self.temperature,
                    max_tokens or self.max_tokens,
                ),
                timeout=self.timeout,
            )
            
            logger.info(f"Groq call successful - {self.model}")
            return response

        except asyncio.TimeoutError:
            logger.error(f"Groq call timed out after {self.timeout}s")
            raise

        except Exception as e:
            logger.error(f"Groq API error: {str(e)}")
            raise

    def _call_sync(self, prompt: str, temperature: float, max_tokens: int) -> str:
        """Synchronous Groq API call (runs in thread pool)"""
        t0 = time.perf_counter()
        response = self.client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=self.model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        elapsed = time.perf_counter() - t0
        usage = getattr(response, "usage", None)
        logger.info(
            "groq_call_timing "
            f"elapsed={elapsed:.2f}s "
            f"prompt_tokens={getattr(usage, 'prompt_tokens', None)} "
            f"completion_tokens={getattr(usage, 'completion_tokens', None)} "
            f"groq_total_time={getattr(usage, 'total_time', None)} "
            f"groq_queue_time={getattr(usage, 'queue_time', None)} "
            f"finish_reason={response.choices[0].finish_reason}"
        )
        return response.choices[0].message.content

    async def parse_json_response(self, prompt: str) -> dict:
        """Call Groq and parse JSON response"""
        response = await self.call(prompt)
        
        # Clean up markdown code blocks if present
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        
        response = response.strip()
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {response[:200]}")
            raise ValueError(f"Invalid JSON response from Groq: {str(e)}")

    async def test_connection(self) -> bool:
        """Test if Groq API is accessible"""
        try:
            response = await self.call("Say 'OK' in one word only")
            return response.strip().lower() == "ok"
        except Exception as e:
            logger.error(f"Groq connection test failed: {str(e)}")
            return False