# C:\Users\Rahul\Agent-flow\services\llm_service.py
"""
Centralized Async LLM Service with Per-Agent Configuration
Universal provider support - works with ANY LLM API
Each agent creates its own service instance for concurrent processing
Async implementation for high performance
"""
import logging
import asyncio
import aiohttp
import tiktoken
from typing import Tuple, Optional, Dict, Any
from config.settings import config

logger = logging.getLogger(__name__)

# Statistics tracking
llm_stats = {
    'total_calls': 0,
    'total_tokens': 0,
    'total_errors': 0,
    'calls_by_agent': {
        'planner': 0,
        'assembler': 0,
        'developer': 0,
        'reviewer': 0,
        'sonarqube': 0
    }
}


class LLMService:
    """Unified async LLM service supporting all providers"""

    def __init__(self, api_key: str, api_url: str):
        """
        Initialize LLM service with specific API credentials

        Args:
            api_key: API key for the LLM provider
            api_url: API endpoint URL
        """
        if not api_key:
            raise ValueError("API key not provided")

        if not api_url:
            raise ValueError("API URL not provided")

        self.api_key = api_key
        self.api_url = api_url
        self._session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=180)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        """Close the aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def call(
        self,
        prompt: str,
        agent_name: str = "general",
        max_tokens: Optional[int] = None,
        temperature: float = 0.3,
        model: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ) -> Tuple[str, int]:
        """
        Universal async LLM call method supporting all providers

        Args:
            prompt: The prompt text to send
            agent_name: Name of the calling agent (for stats and model selection)
            max_tokens: Maximum tokens to generate (None = no limit)
            temperature: Sampling temperature
            model: Override model (if None, uses agent-specific model from config)
            max_retries: Number of retry attempts for rate limits
            retry_delay: Base delay between retries (exponential backoff)

        Returns:
            Tuple of (response_content, tokens_used)
        """
        # Select model based on agent
        model_to_use = model or self._get_agent_model(agent_name)

        if not model_to_use:
            raise ValueError(f"No model configured for agent '{agent_name}'. Check .env file.")

        # Call provider with retries
        for attempt in range(max_retries):
            try:
                # Rate limiting
                await asyncio.sleep(0.1)

                # Universal provider call - detects format from API URL
                content, tokens = await self._call_provider(
                    prompt, model_to_use, max_tokens, temperature
                )

                # Update statistics
                llm_stats['total_calls'] += 1
                llm_stats['total_tokens'] += tokens
                if agent_name in llm_stats['calls_by_agent']:
                    llm_stats['calls_by_agent'][agent_name] += 1

                logger.debug(f"[{agent_name}] LLM call successful. Tokens: {tokens}")
                return content, tokens

            except aiohttp.ClientResponseError as e:
                if e.status == 429:  # Rate limit
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(
                            f"Rate limit hit (attempt {attempt + 1}/{max_retries}), "
                            f"waiting {wait_time}s before retry..."
                        )
                        await asyncio.sleep(wait_time)
                        continue

                logger.error(f"HTTP Error: {e}")
                llm_stats['total_errors'] += 1
                raise Exception(f"LLM API call failed: {e}")

            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                llm_stats['total_errors'] += 1
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    logger.warning(f"Retrying after {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                raise Exception(f"LLM call error: {e}")

        raise Exception(f"Max retries ({max_retries}) exceeded for LLM call")

    def call_sync(
        self,
        prompt: str,
        agent_name: str = "general",
        max_tokens: Optional[int] = None,
        temperature: float = 0.3,
        model: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ) -> Tuple[str, int]:
        """Synchronous wrapper for async call method"""
        import concurrent.futures

        def run_in_thread():
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                return loop.run_until_complete(
                    self.call(prompt, agent_name, max_tokens, temperature, model, max_retries, retry_delay)
                )
            finally:
                try:
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()
                    if pending:
                        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                    loop.close()
                except Exception as e:
                    logger.debug(f"Error cleaning up event loop: {e}")
                finally:
                    asyncio.set_event_loop(None)

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_in_thread)
            return future.result(timeout=200)

    def _get_agent_model(self, agent_name: str) -> Optional[str]:
        """Get model name for specific agent from config"""
        model_map = {
            'planner': config.PLANNER_LLM_MODEL,
            'assembler': config.ASSEMBLER_LLM_MODEL,
            'developer': config.DEVELOPER_LLM_MODEL,
            'reviewer': config.REVIEWER_LLM_MODEL,
            'rebuilder': config.DEVELOPER_LLM_MODEL,  # Rebuilder uses developer config
            'sonarqube': config.DEVELOPER_LLM_MODEL  # SonarQube uses developer config
        }
        return model_map.get(agent_name)

    async def _call_provider(
        self,
        prompt: str,
        model: str,
        max_tokens: Optional[int],
        temperature: float
    ) -> Tuple[str, int]:
        """Universal provider call - uses the exact URL provided by user, auto-detects API format from response"""
        session = await self._get_session()

        # Build the API URL - replace {model} placeholder if present (for Gemini)
        api_url = self.api_url.replace("{model}", model)

        # Prepare headers
        headers = {"Content-Type": "application/json"}

        # Detect provider format ONLY from URL for specific header requirements
        # Gemini uses API key in URL, others use Authorization header
        if "generativelanguage.googleapis.com" in self.api_url.lower():
            # Gemini-specific: API key in URL query parameter
            api_url += f"&key={self.api_key}" if "?" in api_url else f"?key={self.api_key}"
        else:
            # All other providers: Authorization header (OpenAI, Groq, OpenRouter, Local LLMs, etc.)
            headers["Authorization"] = f"Bearer {self.api_key}"

        # Add optional headers for specific providers (doesn't affect functionality)
        if "openrouter.ai" in self.api_url.lower():
            headers["HTTP-Referer"] = "https://github.com/agent-flow"
            headers["X-Title"] = "Agent Flow"
        elif "groq.com" in self.api_url.lower():
            headers["HTTP-Referer"] = "https://github.com/agent-flow"

        # Prepare request data based on API format (Gemini vs OpenAI-compatible)
        if "generativelanguage.googleapis.com" in self.api_url.lower():
            # Gemini API format
            generation_config = {"temperature": temperature}
            if max_tokens is not None:
                generation_config["maxOutputTokens"] = max_tokens

            data = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": generation_config
            }
            extract_content = lambda r: r['candidates'][0]['content']['parts'][0]['text']
            extract_tokens = lambda r: r.get('usageMetadata', {}).get('totalTokenCount', 0)
        else:
            # OpenAI-compatible format (OpenAI, Groq, OpenRouter, Local LLMs, etc.)
            # Detect model type for parameter handling
            model_lower = model.lower()

            # Check if it's a reasoning model (o1 series) - these have special requirements
            is_reasoning_model = any(keyword in model_lower for keyword in [
                "o1-preview", "o1-mini", "o1",
                "o3-preview", "o3-mini", "o3"
            ])

            # Check if it's a GPT-5 model - these have temperature restrictions
            is_gpt5_model = "gpt-5" in model_lower

            if is_reasoning_model:
                # Reasoning models: Use max_completion_tokens, no temperature
                logger.info(f"Detected reasoning model: {model}. Using max_completion_tokens, no temperature.")
                data = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}]
                }
                if max_tokens is not None:
                    data["max_completion_tokens"] = max_tokens
            elif is_gpt5_model:
                # GPT-5 models: No temperature parameter (only default supported)
                logger.info(f"Detected GPT-5 variant: {model}. Omitting temperature parameter.")
                data = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}]
                }
                if max_tokens is not None:
                    data["max_tokens"] = max_tokens
            else:
                # Standard models: Full parameter support (GPT-4, Groq models, local LLMs, etc.)
                data = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature
                }
                if max_tokens is not None:
                    data["max_tokens"] = max_tokens

            extract_content = lambda r: r['choices'][0]['message']['content']
            extract_tokens = lambda r: r.get('usage', {}).get('total_tokens', 0)

        # Make the API call to the URL provided in .env
        async with session.post(api_url, headers=headers, json=data) as response:
            response_text = await response.text()

            # Log response for debugging
            if response.status != 200:
                logger.error(f"API Error Response: Status {response.status}, Body: {response_text}")

            response.raise_for_status()

            # Try to parse JSON response
            try:
                response_data = await response.json()
            except Exception as json_error:
                # Local LLMs or custom APIs may return malformed JSON
                logger.warning(f"JSON parsing failed: {json_error}. Attempting to fix malformed JSON...")

                # Try to fix common JSON issues
                try:
                    import re
                    import json

                    # Remove BOM and control characters
                    cleaned_text = response_text.strip()
                    cleaned_text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned_text)

                    # Try to extract JSON if wrapped in text
                    json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
                    if json_match:
                        cleaned_text = json_match.group(0)

                    # Fix single quotes to double quotes
                    cleaned_text = cleaned_text.replace("'", '"')

                    # Try parsing again
                    response_data = json.loads(cleaned_text)
                    logger.info("Successfully parsed malformed JSON")

                except Exception as retry_error:
                    # If still fails, create a compatible response structure
                    logger.warning(f"Could not parse response as JSON: {retry_error}. Using raw text as content.")

                    # Create appropriate response structure based on API format
                    if "generativelanguage.googleapis.com" in self.api_url.lower():
                        # Gemini format
                        response_data = {
                            'candidates': [{
                                'content': {
                                    'parts': [{'text': response_text}]
                                }
                            }],
                            'usageMetadata': {'totalTokenCount': 0}
                        }
                    else:
                        # OpenAI-compatible format (default for most APIs)
                        response_data = {
                            'choices': [{
                                'message': {
                                    'content': response_text
                                }
                            }],
                            'usage': {'total_tokens': 0}
                        }
                    logger.info("Created fallback response structure")

        # Extract content and tokens
        try:
            content = extract_content(response_data)
        except Exception as extract_error:
            logger.warning(f"Content extraction failed: {extract_error}. Using raw response text.")
            # Fallback: use the raw text if extraction fails
            content = response_text

        try:
            tokens = extract_tokens(response_data)
        except Exception:
            tokens = 0

        # Fallback to estimation if no token count provided
        if tokens == 0:
            tokens = self._estimate_tokens(prompt, content)

        return content, tokens

    def _estimate_tokens(self, prompt: str, content: str) -> int:
        """Estimate token count using tiktoken"""
        try:
            encoder = tiktoken.get_encoding("cl100k_base")
            return len(encoder.encode(prompt)) + len(encoder.encode(content))
        except Exception as e:
            logger.warning(f"Token estimation failed: {e}")
            # Rough estimation: ~4 chars per token
            return (len(prompt) + len(content)) // 4

    def get_stats(self) -> Dict[str, Any]:
        """Get LLM service statistics"""
        return llm_stats.copy()


# Helper function to get agent-specific configuration
def get_agent_llm_config(agent_name: str) -> Dict[str, str]:
    """
    Get LLM configuration for specific agent from settings

    Args:
        agent_name: Name of the agent (planner, developer, reviewer, assembler)

    Returns:
        Dict with 'key' and 'url' for the agent
    """
    config_map = {
        'planner': {'key': config.PLANNER_LLM_KEY, 'url': config.PLANNER_LLM_URL},
        'assembler': {'key': config.ASSEMBLER_LLM_KEY, 'url': config.ASSEMBLER_LLM_URL},
        'developer': {'key': config.DEVELOPER_LLM_KEY, 'url': config.DEVELOPER_LLM_URL},
        'reviewer': {'key': config.REVIEWER_LLM_KEY, 'url': config.REVIEWER_LLM_URL},
        'rebuilder': {'key': config.DEVELOPER_LLM_KEY, 'url': config.DEVELOPER_LLM_URL},
        'sonarqube': {'key': config.DEVELOPER_LLM_KEY, 'url': config.DEVELOPER_LLM_URL}
    }

    agent_config = config_map.get(agent_name)
    if not agent_config or not agent_config['key'] or not agent_config['url']:
        raise ValueError(f"No LLM configuration found for agent '{agent_name}'. Check .env file.")

    return agent_config


# Simplified API for tools to use
async def call_llm_async(
    prompt: str,
    agent_name: str = "general",
    max_tokens: Optional[int] = None,
    temperature: float = 0.3,
    model: Optional[str] = None
) -> Tuple[str, int]:
    """
    Async LLM call with per-agent configuration (creates new service instance per call)

    Each call creates its own service instance - fully concurrent, no global state
    """
    agent_config = get_agent_llm_config(agent_name)
    service = LLMService(agent_config['key'], agent_config['url'])
    try:
        return await service.call(prompt, agent_name, max_tokens, temperature, model)
    finally:
        await service.close()


def call_llm(
    prompt: str,
    agent_name: str = "general",
    max_tokens: Optional[int] = None,
    temperature: float = 0.3,
    model: Optional[str] = None
) -> Tuple[str, int]:
    """
    Synchronous LLM call with per-agent configuration (creates new service instance per call)

    Each call creates its own service instance - fully concurrent, no global state
    """
    agent_config = get_agent_llm_config(agent_name)
    service = LLMService(agent_config['key'], agent_config['url'])
    try:
        return service.call_sync(prompt, agent_name, max_tokens, temperature, model)
    finally:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(service.close())
        loop.close()
