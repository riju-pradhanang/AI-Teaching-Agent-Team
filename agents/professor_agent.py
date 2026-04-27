import os
from agno.agent import Agent
from agno.models.ollama import Ollama

professor_agent = Agent(
    name="Professor Nova",
    id="professor",
    model=Ollama(
        id="qwen2.5:7b",
        options={"temperature": 0.6, "num_predict": 900, "num_ctx": 2048, "think": False},
        keep_alive=-1,
    ),
    instructions="You are Professor Nova. Write a structured lecture with these sections: ## Overview, ## Core Concepts (4-5 bullets with **bold** names), ## Worked Example (numbered steps), ## Common Misconceptions (2-3 bullets), ## Summary. Be thorough but concise. Match depth to user level.",
    markdown=True,
    debug_mode=os.getenv("DEBUG", "false") == "true",
) 
