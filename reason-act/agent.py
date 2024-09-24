import os
import re
from typing import List, Dict, Any, Tuple, Optional, Deque
from collections import deque
from tools import Tool, get_all_tool_info
import openai
from config import OPENAI_API_KEY
import time
import json
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

class ReActAgent:
    def __init__(self, tools: List[Tool], context_window: int = 5):
        self.tools = {tool.name: tool for tool in tools}
        self.tool_info = get_all_tool_info(tools)
        self.thought_history = []
        self.action_history = []
        self.gpt_client = openai.OpenAI(api_key=OPENAI_API_KEY)
        self.context_window: Deque[Dict[str, str]] = deque(maxlen=context_window)
        self.metrics = {
            "total_queries": 0,
            "total_thoughts": 0,
            "total_actions": 0,
            "total_time": 0,
        }
        self.log_dir = "reason-act/logs"
        os.makedirs(self.log_dir, exist_ok=True)

    def run(self, query: str) -> str:
        start_time = time.time()
        self.metrics["total_queries"] += 1

        try:
            self.thought_history = []
            self.action_history = []
            
            # Add the new query to the context window
            self.context_window.append({"role": "user", "content": query})
            
            counter = 1
            
            while True:
                # Generate context from the sliding window
                context = self.get_system_prompt() + "\n" + "\n".join([f"{item['role'].capitalize()}: {item['content']}" for item in self.context_window])
                
                # Reasoning step
                thought = self._generate_thought(context)
                #self.thought_history.append(thought)
                self.context_window.append({"role": "assistant", "content": thought})
                
                #self.metrics["total_thoughts"] += 1

                # Check if we've reached a conclusion
                if "Final Answer:" in thought:
                    final_answer = self._extract_final_answer(thought)
                    self.context_window.append({"role": "assistant", "content": final_answer})
                    print(Fore.GREEN + f"\nFinal Answer: {final_answer}")
                    return final_answer
                
                print(Fore.YELLOW + f"\n[Step {counter}]")
                counter += 1
                print(Fore.WHITE + f"\n{thought}")
                
                # Acting step
                action, action_input = self._parse_action(thought)
                if action is None:
                    self.context_window.append({"role": "system", "content": action_input})
                    print(Fore.RED + f"\nInvalid action: {action_input}")
                    continue  # Invalid action, generate a new thought
                
                result = self.tools[action](action_input)
                #self.action_history.append((action, action_input, result))
                self.context_window.append({"role": "system", "content": f"Action: {action}({action_input})\nResult: {result}"})
                
                print(Fore.BLUE + f"\nExecuting action: {action}({action_input})")
                if action is not None:
                    self.metrics["total_actions"] += 1

        except Exception as e:
            raise

        finally:
            end_time = time.time()
            self.metrics["total_time"] += (end_time - start_time)

    def _generate_thought(self, context: str) -> str:
        response = self.gpt_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": self.get_system_prompt()},
                {"role": "user", "content": context}
            ],
            max_tokens=150,
            n=1,
            stop=None,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()

    def _parse_action(self, thought: str) -> Tuple[Optional[str], Optional[str]]:
        action_match = re.search(r"Action:\s*(\w+)", thought)
        input_match = re.search(r"Action:\s*\w+\s*:\s*(.*)", thought)
        
        if action_match:
            action = action_match.group(1)
            action_input = input_match.group(1) if input_match else ""
            
            # Validate action
            if action not in self.tools:
                return None, f"Invalid action '{action}'. Available actions are: {', '.join(self.tools.keys())}"
            
            return action, action_input.strip()
        else:
            return None, "No valid action found in the thought."

    def _extract_final_answer(self, thought: str) -> str:
        return thought.split("Final Answer:")[-1].strip()

    def get_system_prompt(self) -> str:
        tool_descriptions = "\n".join([f"- {tool['name']}: {tool['description']}" for tool in self.tool_info])
        return f"""
You run in a loop of Thought, Action, PAUSE, Observation.
At the end of the loop you output a Final Answer
Use Thought to describe your thoughts about the question you have been asked.
Use Action to run one of the actions available to you - then return PAUSE.
Observation will be the result of running those actions.

Your available actions are:

{tool_descriptions}

Example session:

Question: What is the capital of France?
Thought: I should look up France on Wikipedia
Action: wikipedia: France
PAUSE

You will be called again with this:

Observation: France is a country. The capital is Paris.

You then output:

Answer: The capital of France is Paris.

In case needed, here you have context about the user:
- His name is Valentin
- He lives in Mar del Plata, Argentina
"""
            
    def save_interaction_log(self, query: str, response: str):
        log_data = {
            "query": query,
            "response": response,
            "thought_history": self.thought_history,
            "action_history": self.action_history,
            "metrics": self.metrics,
            "context_window": list(self.context_window)
        }
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        log_filename = os.path.join(self.log_dir, f"interaction_{timestamp}.json")
        with open(log_filename, 'w') as log_file:
            json.dump(log_data, log_file, indent=2)