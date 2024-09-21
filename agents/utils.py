import os
import json
import asyncio
from datetime import datetime

async def log_interaction(user_prompt, docs_retrieved, llm_answer, rephrased_query):
    log_folder = "logs"
    os.makedirs(log_folder, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_folder, f"interaction_{timestamp}.json")

    log_data = {
        "timestamp": datetime.now().isoformat(),
        "user_prompt": user_prompt,
        "rephrased_query": rephrased_query,
        "docs_retrieved": docs_retrieved,
        "llm_answer": llm_answer
    }

    async def write_log():
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)

    asyncio.create_task(write_log())
