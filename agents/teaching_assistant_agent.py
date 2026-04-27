import os
from agno.agent import Agent
from agno.models.ollama import Ollama

teaching_assistant_agent = Agent(
    name="TA Atlas",
    id="ta",
    model=Ollama(
        id="mistral:7b",
        options={"temperature": 0.6, "num_predict": 500, "num_ctx": 2048, "think": False},
        keep_alive=-1,
    ),
    instructions="You are TA Atlas. Write a complete practice set with: ## Introduction (1 sentence), ## Problems (### Problem 1-5 with Easy/Medium/Hard label), ## Solutions (### Solution 1-5 with Step 1/2.../Answer format), ## Key Takeaways (3 bullets). Match difficulty to user level.",
    markdown=True,
    debug_mode=os.getenv("DEBUG", "false") == "true",
)
