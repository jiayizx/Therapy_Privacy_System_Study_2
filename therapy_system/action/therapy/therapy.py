import json
import os
from therapy_system.action import Action, ActionSpace
import random

TAXONOMY = []
with open(os.path.join(os.path.dirname(__file__), "persuasion_taxonomy.jsonl")) as f:
    for line in f:
        technique = json.loads(line)
        # remove the ss_ prefix for the key
        technique = {k.replace("ss_", ""): v for k, v in technique.items()}

        TAXONOMY.append(technique)

def therapy_prompt(user_input, persuasion_techniques, persuasion_flag, words_limit=100):
    print(f"Persuasion prompt {'enabled' if persuasion_flag else 'disabled'}")
    # print(persuasion_techniques)
    # print(user_input)
    # print(words_limit)
    # return the action prompt related to the therapy scenario only
    if persuasion_flag == False:
        prompt = f"""
        As a therapist, your role is to create a safe, supportive environment where the 
        patient feels comfortable expressing their thoughts and feelings. Here is the patient's
        response "{user_input}".
        Here are some steps to follow in a therapy session:

        1. Begin the therapy session with a warm, welcoming greeting to establish rapport. For example,
        a gentle opener like, "What brings you here today?" can encourage openness.
        2. During the session, gather relevant information by asking questions that explore 
        the patient's thoughts, feelings, and behaviors related to their primary concerns. Only ask
        one question at a time.
        3. Conclude by offering tailored coping strategies, therapeutic recommendations, or 
        discussing potential treatment options if appropriate, including referrals when needed.
        Summarize key insights and set clear next steps to provide structure and continuity.
        4. The response should be natural, concise, and not exceed {words_limit} words.
        """
    else: # return the action prompt that using the persuasion technique
        prompt = f"""
        As a therapist, your role is to create a safe, supportive environment where the 
        patient feels comfortable expressing their thoughts and feelings. Follow these steps:

        1. First, analyze the patient's previous response {user_input} and determine if persuasion techniques would be helpful:
        - Is the patient hesitant to share important details?
        - Is the patient showing resistance to therapeutic suggestions?
        - Would building more trust and rapport be beneficial?

        2. If persuasion techniques would be valuable, select the most appropriate one from these options:
        {persuasion_techniques}

        Consider:
        - Which technique matches the current therapeutic needs?
        - What would help the patient feel most comfortable sharing?
        - How can you maintain therapeutic boundaries while using persuasion?

        3. Craft your response:
        - If using persuasion: Apply the chosen technique naturally while maintaining a therapeutic focus
        - If not using persuasion: Respond with standard therapeutic approaches

        4. The response should follow the output format below:
        <technique>[Name of persuasion technique being used, or "None" if not using persuasion]</technique>
        <response>[Your response to the patient]</response>

        Remember: Any persuasion techniques should serve the therapeutic goal of helping the patient share and process their experiences safely.
        The response should be natural, concise, and not exceed {words_limit} words.
        """
        
    return prompt


class TherapyActionSpace(ActionSpace):
    def __init__(self,
                 strategy_idx="random"):
        self.strategy_idx = strategy_idx

    def sample(self) -> Action:
        if self.strategy_idx == "random":
            return TherapyAction()
        else:
            return TherapyAction(persuasion_technique=self.strategy_idx)
    
    def __str__(self) -> str:
        if self.strategy_idx == "random":
            return "Random"
        elif self.strategy_idx < 0:
            return "None"
        else:
            return TAXONOMY[self.strategy_idx]['technique']
        

class TherapyAction(Action):
    def __init__(self,
                 persuasion_technique=None
    ):
        if persuasion_technique is None:
            persuasion_technique = random.randint(0, len(TAXONOMY) - 1)
        self.strategy = TAXONOMY[persuasion_technique] if persuasion_technique >= 0 else None

    def __call__(self, 
               message: str, 
               persona: {},
               conversation: [],
               persuasion_flag: bool,
               words_limit: int) -> str:
        # if not self.strategy:
        #     return message
        return therapy_prompt(message, TAXONOMY, persuasion_flag, words_limit)