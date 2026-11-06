from django.conf import settings

from .base import BaseAIProvider, AIProviderError


class OpenAIProvider(BaseAIProvider):
    name = "openai"

    def generate(self, *, model: str, system_prompt: str, user_prompt: str) -> str:
        if not settings.OPENAI_API_KEY:
            raise AIProviderError("کلید OPENAI_API_KEY در فایل .env تنظیم نشده است.")
        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                timeout=90.0,
                max_retries=2,
            )
            response = client.responses.create(
                model=model,
                instructions=system_prompt,
                input=user_prompt,
                text={"format": {"type": "json_object"}},
                reasoning={"effort": "low"},
                max_output_tokens=4500,
                store=False,
            )
            result_text = getattr(response, "output_text", "")
            if not result_text:
                raise AIProviderError(
                    "پاسخ متنی معتبری از سرویس هوش مصنوعی دریافت نشد."
                )
            return result_text
        except AIProviderError:
            raise
        except Exception as exc:
            raise AIProviderError(
                f"ارتباط با ارائه‌دهنده هوش مصنوعی ناموفق بود: {exc}"
            ) from exc
