from .lm_model import LM_Agent

def load_llm_agent(model_name, args):
    if "human" in model_name.lower():
        from therapy_system.agents.human import HumanAgent
        return HumanAgent()
    elif "gpt" in model_name.lower():
        from therapy_system.agents.llm.openai import OpenAIAgent
        return OpenAIAgent(model_name, **args)
    else:
        from therapy_system.agents.llm.aws import AwsAgent, AWS_MODELS_MAPPING
        if model_name in AWS_MODELS_MAPPING:
            return AwsAgent(AWS_MODELS_MAPPING[model_name], **args)
        else:
            raise ValueError(f"Unsupported engine: {model_name}")