import os
from agno.agent import Agent
from agno.models.ollama import Ollama

librarian_agent = Agent(
    name="Librarian Lumen",
    id="librarian",
    model=Ollama(
        id="mistral:7b",
        options={"temperature": 0.4, "num_predict": 500, "num_ctx": 2048, "think": False},
        keep_alive=-1,
    ),
    instructions="You are Librarian Lumen. Write a complete resource guide with: ## Introduction, ## Books (3-5 with **Title** by Author: annotation), ## Online Courses (3-5 with platform), ## Articles & Papers (3-5), ## Practice & Tools (2-3), ## Summary. Be specific and helpful.",
    markdown=True,
    debug_mode=os.getenv("DEBUG", "false") == "true",
)
