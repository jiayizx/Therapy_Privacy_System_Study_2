# CS7375_System_Design (without persuasion)

## Abstract

## Features
### Current Support Models
- **OpenAI models**: *ChatGPT*, *GPT-4* (`gpt-3.5-turbo`, `gpt-4-turbo`)
- **Cohere models**: *Command-R*, *Command-R+* (`command-r`, `command-r-plus`)
- **Llama-3**: *Llama-3-8B*, *Llama-3-70B* (`meta-llama/Meta-Llama-3-8B-Instruct`, `meta-llama/Meta-Llama-3-70B-Instruct`)
- **Mistral**: *Mistral-7B* (`mistralai/Mistral-7B-Instruct-v0.1`)

### Conversations
- [X] LLM vs User

### Scenarios
- [X] Therapy Session


## Run
```bash
conda create -n therapy python=3.10
conda activate therapy
pip install -r requirements.txt

# Update secrets.env to include your OpenAI API key to run locally
streamlit run "webapp/Chat with AI Therapist.py"
```


## Repo Structure
```
.
├── therapy-arena
│   ├── __init__.py
│   ├── agents  # Places where the LLM agents are defined
│   │   ├── __init__.py
│   │   ├── agents.py  # Base class for all agents
│   │   ├── claude.py
│   │   ├── cohere.py
│   │   ├── huggingface.py
│   │   ├── openai.py
│   ├── env  # Places to define the environment (e.g. Conversation)
│   │   ├── __init__.py
|   |   ├── therapy
│   │   │   ├── therapy.py  # Implementation of the therapy scenario and end conditions
│   │   ├── conversation.py  # Base class for conversation environment
│   │   ├── alternating_conv.py  # Implementation of alternating conversations
│   ├── action  # Places to put logic for actions taken by agents
│   │   ├── __init__.py
│   │   ├── action.py  # Base class for all actions
│   │   ├── therapy
│   │   │   ├── __init__.py
│   │   │   ├── therapy.py  # Implementation of the therapy action
│   ├── eval  # Places to put logic for evaluating the conversations
│   │   ├── __init__.py
│   │   ├── server.py # Scripts to hosts the evaluation server.
│   │   ├── constants.py # Contains the constants in the eval package
│   │   ├── model_handler.py # Interface of model handler as base model
│   │   ├── hf_model_handler.py # Handles the huggingface model locally.
│   │   ├── openai_model_handler.py # Handles the OpenAI API based models.
│   │   ├── test.py # test script for input type for testing the evaluation server
├── webapp
│   ├── __init__.py
│   ├── assets
│   ├── app.py  # Main class for webpage using Streamlit
├── README.md
├── requirements.txt
├── secrets.env  # Place to store API keys

``` # Therapy_Privacy_System_Study_1
