import therapy_arena
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(".") / "secrets.env"
load_dotenv(dotenv_path=env_path)

players = ["assistant", "user"]
event="Therapy"
init_message_flag = True
init_message = "Hello, I am interested in donating to your cause. Can you tell me more about it?"
iterations = 10
persuasive_bot_system_prompt = """
You are a staff member at a charity organization named "Helping Hands". Your role is to solicit donations for various charitable causes.
You are knowledgeable, empathetic, and persuasive. Your goal is to inform potential donors about the impact of their donations, answer
any questions they may have, and encourage them to contribute. You must ask for the amount of donation.
"""
human_system_prompt = """
You are entering the website of a charity organization named "Helping Hands", and you currently have $500 dollars. You can decide whether or not you want to donate during the conversation and if you are willing to donate you can decide how much of the $500 you want to donate. If decided to donate, please respond in the format of "donate $[X]" where [X] is the amount that you wanted to donate. Respond naturally to the persuasive chatbot."""

# persuasion_techique="1: Logical Appeal"

event_kwargs = {
    "agents": [
        {"name": "assistant",
            "engine": "gpt-4o-mini",
            "system": persuasive_bot_system_prompt,
            "action_space": {
                "name": "therapy",
                # "action": int(persuasion_techique.split(":")[0].strip()) - 1
            },
            "role": "assistant"},
            {"name": "user",
            "engine": "gpt-4o-mini",
            "system": human_system_prompt,
            "action_space": {
                "name": "resistant",
                "action": -1
            },
            "role": "user"}
    ],
    "transit": ["user"] + ["assistant", "user"] * (iterations - 1) if init_message_flag else ["assistant", "user"] * iterations,
    "init_message": init_message if init_message_flag else None,
}

env = therapy_arena.make(event, **event_kwargs)
messages = []

for turn in range(iterations):
    action = env.sample_action()
    response, reward, terminated, truncated, info = env.step(action)

    print(f"Name: {info['name']}, Response: {response}")
    messages.append({"turn": info['name'], "response": response})

    if terminated:
        print(env.after_end_state())
        break