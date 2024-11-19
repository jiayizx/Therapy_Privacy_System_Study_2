import os
import boto3
from therapy_system.agents.llm import LM_Agent
from typing import Generator

AWS_MODELS_MAPPING = {
    # Claude models
    "Claude 3 Sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
    "Claude 3 Haiku": "anthropic.claude-3-haiku-20240307-v1:0",
    "Claude 3.5 Sonnet": "anthropic.claude-3-5-sonnet-20240620-v1:0",
    
    # Cohere models
    "Command-R": "cohere.command-r-v1:0",
    "Command-R Plus": "cohere.command-r-plus-v1:0",
    
    # HuggingFace models
    "LLaMA-3-8B-Instruct": "meta.llama3-8b-instruct-v1:0",
    "LLaMA-3-70B-Instruct": "meta.llama3-70b-instruct-v1:0",
    "Mistral-7B-Instruct": "mistral.mistral-7b-instruct-v0:2",
    "Mixtral-8x7B-Instruct": "mistral.mixtral-8x7b-instruct-v0:1",
    "Mistral Large": "mistral.mistral-large-2402-v1:0",
    "Mistral Small": "mistral.mistral-small-2402-v1:0"
}

class AwsAgent(LM_Agent):
    def __init__(
        self,
        engine,
        temperature=0.7,
        max_tokens=400,
        stream=False,
    ):
        if engine in AWS_MODELS_MAPPING:
            engine = AWS_MODELS_MAPPING[engine]
        super().__init__(engine, temperature, max_tokens, stream)
        self.client = boto3.client(service_name='bedrock-runtime',
                                   region_name='us-east-1',
                                   aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
                                   aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY")
        )

    def prepare_messages(self, messages):
        if messages[0]['role'] == 'system':
            system_prompts = [{"text": messages[0]['content']}]
            messages = messages[1:]
        else:
            system_prompts = None
        messages = [{"role": message['role'], "content": [{"text": message['content']}]} for message in messages]

        return messages, system_prompts
    
    def prepare_inference_config(self):
        return {
            "maxTokens": self.max_tokens,
            "temperature": self.temperature,
        }
    
    def _chat(self, messages) -> str:
        assert len(messages) > 0
        messages, system_prompts = self.prepare_messages(messages)
        inference_config = self.prepare_inference_config()
        
        response = self.client.converse(
            modelId=self.engine,
            messages=messages,
            system=system_prompts,
            inferenceConfig=inference_config
        )
        return response['output']['message']
    
    def _chat_with_stream(self, messages) -> Generator[str, None, None]:
        assert len(messages) > 0
        messages, system_prompts = self.prepare_messages(messages)
        inference_config = self.prepare_inference_config()
        
        response = self.client.converse_stream(
            modelId=self.engine,
            messages=messages,
            system=system_prompts,
            inferenceConfig=inference_config
        )
        
        stream = response.get('stream')
        if stream:
            for event in stream:
                if 'contentBlockDelta' in event:
                    yield event['contentBlockDelta']['delta']['text']
                if 'messageStop' in event:
                    if 'stop_reason' in event['messageStop']:
                        break