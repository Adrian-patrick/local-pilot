import json
import logging
import os
import re
import time
from typing import Iterator

from app.agent.prompts import build_react_system_prompt
from app.agent.tools import AVAILABLE_TOOLS
from app import groq_service
from app import ollama_service

log = logging.getLogger(__name__)


class AgentOrchestrator:
    def __init__(self, model: str, base_dir: str):
        self.is_groq = model.startswith("groq:")
        self.model = model.split("groq:")[1] if self.is_groq else model
        
        self.base_dir = os.path.abspath(base_dir)
        self.api_key = os.getenv("groq_api_key") or os.getenv("GROQ_API_KEY")
        self.system_prompt = build_react_system_prompt(self.base_dir)
        # Structured message history for proper role separation
        self.messages: list[dict] = [
            {"role": "system", "content": self.system_prompt}
        ]
        self.tools_used = set()

    def _resolve_path(self, path: str) -> str:
        """Resolve a path. If it's already absolute, use it as-is. Otherwise join with base_dir."""
        if os.path.isabs(path):
            return os.path.normpath(path)
        return os.path.normpath(os.path.join(self.base_dir, path))

    def _truncate_messages(self):
        """Truncate message history if it's getting too long, keeping system prompt and recent messages."""
        # Estimate total content length
        total_chars = sum(len(m.get("content", "")) for m in self.messages)
        if total_chars > 20000:
            # Keep system prompt (index 0) and the last 6 messages
            self.messages = [self.messages[0]] + self.messages[-6:]

    def run(self, task: str, on_rate_limit=None) -> Iterator[str]:
        """Runs the ReAct loop until 'Final Answer' is reached."""
        if self.is_groq and not self.api_key:
            yield "[Error: Groq API key required for Cloud Agent Mode]\n"
            return

        # Add the user's task as a proper user message
        self.messages.append({"role": "user", "content": task})

        max_iterations = 15
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
                    if self.is_groq:
                        stream = groq_service.ask_groq_stream_messages(
                            self.model, self.messages, self.api_key, on_rate_limit
                        )
                    else:
                        stream = ollama_service.ask_ollama_stream_messages(
                            self.model, self.messages
                        )
                        
                    for token in stream:
                        current_response += token
                        yield token

                        if "PAUSE" in current_response:
                            action_found = True
                            break
                    break  # Success, break out of retry loop

                except Exception as e:
                    err_msg = str(e)
                    if "429" in err_msg or "rate_limit_exceeded" in err_msg.lower():
                        retry_count += 1
                        yield f"\n[⏳ Agent hit Rate Limit. Pausing for 15 seconds before retry {retry_count}/{max_retries}...]\n"
                        time.sleep(15)
                        current_response = ""
                        continue
                    elif "413" in err_msg or "Request too large" in err_msg:
                        yield f"\n[⚠ Agent memory overflow (413). Trimming context and retrying...]\n"
                        self._truncate_messages()
                        retry_count += 1
                        current_response = ""
                        continue
                    else:
                        yield f"\n[Agent Error: {err_msg}]\n"
                        return

            if retry_count >= max_retries:
                yield "\n[Agent Error: Max retries exceeded due to API limits.]\n"
                return

            # Store the assistant's response as a proper assistant message
            self.messages.append({"role": "assistant", "content": current_response})

            if "Final Answer:" in current_response:
                # Interception logic: prevent agent from skipping file creation
                task_requires_file = any(word in task.lower() for word in ["create", "write", "save", "make a file"])
                if task_requires_file and "write_file" not in self.tools_used:
                    interception_msg = "\n\n🚨 [System Interception: You attempted to finish the task, but you have not written any files to the disk yet. You MUST use the `write_file` tool to complete this task.]\n"
                    yield interception_msg
                    
                    # Feed the interception back as a simulated observation so the agent corrects itself
                    self.messages.append({"role": "user", "content": "Observation: System Error - You forgot to use the `write_file` tool. Outputting markdown in chat does not save a file. Please use the `write_file` tool now."})
                    continue
                
                return  # Task complete

            if action_found:
                # Parse action and input using DOTALL to handle multiline JSON strings
                action_match = re.search(r"Action:\s*(.+)", current_response)
                input_match = re.search(r"Action Input:\s*(.*?)(?:\nPAUSE|\Z)", current_response, re.DOTALL)

                if action_match and input_match:
                    action_name = action_match.group(1).strip()
                    input_str = input_match.group(1).strip()
                    
                    yield f"\n\n🔧 [Executing: {action_name}]\n"

                    try:
                        args = None
                        # strict=False allows unescaped literal newlines inside JSON strings
                        try:
                            args = json.loads(input_str, strict=False)
                        except json.JSONDecodeError:
                            # Fallback: keep removing characters from the end until it parses
                            # (solves the extra `} }` garbage issue)
                            temp_str = input_str
                            while temp_str:
                                try:
                                    args = json.loads(temp_str, strict=False)
                                    break
                                except json.JSONDecodeError:
                                    temp_str = temp_str[:-1]
                                    while temp_str and not temp_str.endswith('}'):
                                        temp_str = temp_str[:-1]
                            
                            if args is None:
                                # If it completely fails, raise original error to let it retry
                                raise json.JSONDecodeError("Extra data", input_str, 0)

                        # Resolve paths properly (handles both absolute and relative)
                        if "directory" in args:
                            args["directory"] = self._resolve_path(args["directory"])
                        if "file_path" in args:
                            args["file_path"] = self._resolve_path(args["file_path"])

                        if action_name in AVAILABLE_TOOLS:
                            self.tools_used.add(action_name)
                            result = AVAILABLE_TOOLS[action_name](**args)
                        else:
                            result = f"Error: Unknown tool '{action_name}'. Available tools: {list(AVAILABLE_TOOLS.keys())}"
                    except json.JSONDecodeError:
                        result = "Error: Action Input is not valid JSON. Make sure to use double quotes and escape backslashes (use \\\\ in paths)."
                    except Exception as e:
                        result = f"Error executing tool: {e}"

                    # Feed the observation back as a user message (simulating the environment)
                    observation_msg = f"Observation: {result}"
                    self.messages.append({"role": "user", "content": observation_msg})
                    yield f"📋 [Observation: {len(result)} chars received]\n\n"
                else:
                    error_obs = "Observation: Error: Could not parse Action and Action Input. Use the exact format:\nAction: tool_name\nAction Input: {\"key\": \"value\"}\nPAUSE"
                    self.messages.append({"role": "user", "content": error_obs})
                    yield "\n[⚠ Agent format error, retrying...]\n"
            else:
                # If no pause and no final answer, nudge it
                nudge = "Observation: You didn't call a tool (PAUSE) or provide a Final Answer. Please either use a tool or write 'Final Answer: ...' to respond."
                self.messages.append({"role": "user", "content": nudge})

        yield "\n[Agent reached maximum iterations without completing the task.]\n"
