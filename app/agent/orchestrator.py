import json
import logging
import os
import re
from typing import Iterator

from app.agent.prompts import REACT_SYSTEM_PROMPT
from app.agent.tools import AVAILABLE_TOOLS
from app import groq_service

log = logging.getLogger(__name__)

class AgentOrchestrator:
    def __init__(self, model: str, base_dir: str):
        self.model = model
        self.base_dir = base_dir
        self.api_key = os.getenv("groq_api_key") or os.getenv("GROQ_API_KEY")
        self.history = ""

    def run(self, task: str, on_rate_limit=None) -> Iterator[str]:
        """Runs the ReAct loop until 'Final Answer' is reached."""
        if not self.api_key:
            yield "[Error: Groq API key required for Agent Mode]\n"
            return
            
        if self.model.startswith("groq:"):
            self.model = self.model.split("groq:")[1]
            
        self.history = f"{REACT_SYSTEM_PROMPT}\n\nQuestion: {task}\n"
        
        max_iterations = 10
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Stream the LLM response
            current_response = ""
            action_found = False
            
            # Retry loop for API limits
            max_retries = 3
            retry_count = 0
            while retry_count < max_retries:
                try:
                    for token in groq_service.ask_groq_stream(self.model, self.history, self.api_key, on_rate_limit):
                        current_response += token
                        yield token
                        
                        if "PAUSE" in current_response:
                            action_found = True
                            break
                    break # Success, break out of retry loop
                            
                except Exception as e:
                    err_msg = str(e)
                    if "429" in err_msg or "rate_limit_exceeded" in err_msg.lower():
                        retry_count += 1
                        yield f"\n[Agent hit Rate Limit. Pausing for 15 seconds before retry {retry_count}/{max_retries}...]\n"
                        import time
                        time.sleep(15)
                        current_response = "" # reset for retry
                        continue
                    elif "413" in err_msg or "Request too large" in err_msg:
                        # Context window blown out. We must truncate history to recover.
                        yield f"\n[Agent memory overflow (413). Truncating old context and retrying...]\n"
                        # Keep the system prompt (first 1000 chars roughly) and the most recent 12000 chars
                        if len(self.history) > 13000:
                            self.history = self.history[:1000] + "\n...[EARLY HISTORY TRUNCATED]...\n" + self.history[-12000:]
                        retry_count += 1
                        current_response = ""
                        continue
                    else:
                        yield f"\n[Agent Error: {err_msg}]\n"
                        return
                        
            if retry_count >= max_retries:
                yield "\n[Agent Error: Max retries exceeded due to API limits.]\n"
                return
                
            self.history += current_response
            
            if "Final Answer:" in current_response:
                return # Task complete
                
            if action_found:
                # Parse action and input
                action_match = re.search(r"Action:\s*(.+)", current_response)
                input_match = re.search(r"Action Input:\s*(.+)", current_response)
                
                if action_match and input_match:
                    action_name = action_match.group(1).strip()
                    input_str = input_match.group(1).strip()
                    
                    yield f"\n\n[Agent executing tool: {action_name}]\n"
                    
                    try:
                        args = json.loads(input_str)
                        # Secure paths if necessary
                        if "directory" in args:
                            args["directory"] = os.path.join(self.base_dir, args["directory"])
                        if "file_path" in args:
                            args["file_path"] = os.path.join(self.base_dir, args["file_path"])
                            
                        if action_name in AVAILABLE_TOOLS:
                            result = AVAILABLE_TOOLS[action_name](**args)
                        else:
                            result = f"Error: Unknown tool '{action_name}'"
                    except json.JSONDecodeError:
                        result = "Error: Action Input is not valid JSON."
                    except Exception as e:
                        result = f"Error executing tool: {e}"
                        
                    observation = f"\nObservation: {result}\n"
                    # We don't yield the full observation to the UI to avoid spamming it with giant file contents,
                    # just yield a summary.
                    yield f"[Observation received: {len(result)} chars]\n\n"
                    self.history += observation
                else:
                    self.history += "\nObservation: Error: Could not parse Action and Action Input. Please use correct format.\n"
                    yield "\n[Agent parsing error, retrying...]\n"
            else:
                # If no pause and no final answer, force it to continue
                self.history += "\nObservation: You didn't PAUSE or provide a Final Answer.\n"
                
        yield "\n[Agent reached maximum iterations without completing the task.]\n"
