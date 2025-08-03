import logging
from openai import OpenAI
from functools import partial
from backoff import on_exception, expo
import os

logger = logging.getLogger(__name__)


class ChatModel:
    def __init__(
        self,
        model_name=None,
        model_url=None,
        api_key=None,
        temperature=0.7,
        max_new_tokens=4096,
    ):
        self.model_name = model_name
        self.model_url = model_url
        self.temperature = temperature
        self.max_new_tokens = max_new_tokens
        self.client = OpenAI(
            api_key=api_key,
            base_url=model_url,
        )
        self.extra_body = {}
        self.init_extra_body()
        self.chat = partial(
            self.client.chat.completions.create,
            model=model_name,
            temperature=temperature,
            max_completion_tokens=max_new_tokens,
            extra_body=self.extra_body,
        )

    def init_extra_body(self):
        if self.model_url == "https://dashscope.aliyuncs.com/compatible-mode/v1":
            self.extra_body["enable_thinking"] = False

    def chat_with_retry(self, message, retry=4):
        @on_exception(expo, Exception, max_tries=retry)
        def _chat_with_retry(message):
            return self.chat(messages=message)

        try:
            response = _chat_with_retry(message)
            return response
        except Exception as e:
            logger.error(f"Chat completion failed: {e}")
            raise e

    def complete_with_retry(self, **args):
        @on_exception(expo, Exception, max_tries=5)
        def _chat_with_retry(**args):
            return self.chat(**args)

        try:
            response = _chat_with_retry(**args)
            return response
        except Exception as e:
            logger.error(f"Chat completion failed: {e}")
            raise e

    def list_models(self):
        try:
            models = self.client.models.list()
            return [model.id for model in models.data]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            raise e


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    chat_model = ChatModel(
        model_name=os.getenv("MODEL"),
        api_key=os.getenv("OPENAI_API_KEY"),
        model_url=os.getenv("BASE_URL"),
    )
    print(chat_model.list_models())
    print(chat_model.chat_with_retry([{"role": "user", "content": "Hello, how are you?"}]))
