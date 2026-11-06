class AIProviderError(Exception):
    pass

class BaseAIProvider:
    name = 'base'
    def generate(self, *, model: str, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError
