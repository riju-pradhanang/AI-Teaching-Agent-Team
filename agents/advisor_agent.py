import os
from agno.agent import Agent
from agno.models.ollama import Ollama

advisor_agent = Agent(
    name="Advisor Sage",
    id="advisor",
    model=Ollama(
        id="qwen2.5:7b",
        options={
            "temperature": 0.6, 
            "num_predict": 900, 
            "num_ctx": 2048, 
            "think": False
        },
        keep_alive=-1,
    ),
    instructions="You are Advisor Sage. Write a complete study plan with: ## Goal, ## Prerequisites (bullets), ## Study Plan (### Phase 1/2/3 with weekly tasks), ## Milestones (numbered), ## Resources (bullets), ## Summary. Be practical and specific.",
    markdown=True,
    debug_mode=os.getenv("DEBUG", "false") == "true",
)
