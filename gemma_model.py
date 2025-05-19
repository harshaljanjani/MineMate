import os
import json
from google import genai
try:
    api_key = os.environ.get("GEMMA_API_KEY")
    if not api_key:
        raise ValueError("GEMMA_API_KEY environment variable not set.")
    client = genai.Client(api_key=api_key)
    print("GenAI client initialized successfully.")
except Exception as e:
    print(f"Fatal: Error initializing GenAI client: {e}")
    client = None

# Subjective: I've kept a sliding window to reduce token usage when interacting with the 
# Google AI Studio API. If you're on a paid plan, you may increase this limit as needed.
MAX_HISTORY_TURNS = 5

def format_history_for_prompt(history):
    if not history:
        return ""
    
    formatted_history_parts = []
    for user_cmd, assistant_resp_raw in history:
        conversational_part_for_history = ""
        json_start_index = assistant_resp_raw.find('{')
        if json_start_index == -1:
            conversational_part_for_history = assistant_resp_raw.strip()
        else:
            text_before_json = assistant_resp_raw[:json_start_index].strip()
            if text_before_json:
                conversational_part_for_history = text_before_json
        if conversational_part_for_history:
            formatted_history_parts.append(f"Previous User: {user_cmd}\nPrevious Assistant: {conversational_part_for_history}")         
    if not formatted_history_parts:
        return ""
    return "\n\nConversation History (chronological, most recent is last):\n" + "\n\n".join(formatted_history_parts) + "\n\n---\n\nCurrent Interaction:"

def generate_response(command, history=None):
    if not client:
        return {"raw_response": "GenAI client not initialized.", "error": "Client not initialized"}
    history_prompt_segment = format_history_for_prompt(history or [])
    prompt = f"""You are a friendly and slightly jovial smart home assistant.
    {history_prompt_segment}
    Given the current command (and considering the conversation history if provided), determine if it's a smart home instruction or a general query.

    If it's a smart home instruction:
    1. Provide a short, friendly, conversational acknowledgement.
    2. On a NEW LINE, provide a JSON object with the following structure:
       {{
         "commands": [
           {{"action": "action_name", "device": "device_name", "room": "room_name"}},
           ...
         ],
         "repeat": <number_of_times_to_repeat_the_entire_commands_list> OR "infinite",
         "delay_ms": <optional_delay_in_milliseconds_after_each_command_in_the_list>
       }}
       - "commands": A list of one or more command objects.
       - "action": Valid actions: turn_on, turn_off, lock, unlock, open, close.
       - "device": The name of the device (e.g., lights, door, fan).
       - "room": Valid rooms: living room, kitchen, bedroom, bathroom, office, main.
       - "repeat": How many times the entire sequence in "commands" should be executed.
                   Use "infinite" for tasks that should run continuously until a new command is given (e.g., "flicker the lights").
                   If not specified or not applicable for a single, non-repeating task, default to 1.
       - "delay_ms": An optional delay in milliseconds to apply after *each* command in the "commands" list is executed.
                     IMPORTANT: If a delay is used, it must be at least 500ms.
                     If the user asks to "flicker" or "blink", a small delay_ms (e.g., 200-500) is appropriate.
                     If the user specifies a delay, use that. If the task implies a natural delay or sequence, deduce a reasonable one.

    If it's a general query, provide a conversational answer with a warm and slightly jovial tone, considering the history for context.
    Format your entire response clearly for display in a terminal.

    Smart Home Examples:
    Command: Turn on the lights in the kitchen.
    Response:
    Okay, I'll get those kitchen lights for you!
    {{"commands": [{{"action": "turn_on", "device": "lights", "room": "kitchen"}}], "repeat": 1}}

    Command: Lock the main door.
    Response:
    You got it! Locking the main door now.
    {{"commands": [{{"action": "lock", "device": "door", "room": "main"}}], "repeat": 1}}

    Command: Flicker the bedroom lights for a bit.
    Response:
    Alright, making the bedroom lights flicker!
    {{"commands": [{{"action": "turn_on", "device": "lights", "room": "bedroom"}}, {{"action": "turn_off", "device": "lights", "room": "bedroom"}}], "repeat": "infinite", "delay_ms": 500}}

    Command: Turn on the office fan, then after 5 seconds, turn it off.
    Response:
    Sure thing! I'll turn the office fan on, then off after 5 seconds.
    {{"commands": [{{"action": "turn_on", "device": "fan", "room": "office"}}, {{"action": "turn_off", "device": "fan", "room": "office"}}], "repeat": 1, "delay_ms": 5000}}
    (This means: turn on fan, wait 5000ms, turn off fan. The delay_ms applies after each command in the list for that repetition. The ComputerCraft script will also wait 5000ms after the 'turn_off' if repeat is 1.)

    Command: Turn on lights in living room, then kitchen lights, then bedroom lights, with 1 second between each.
    Response:
    Okay, turning on those lights in sequence with a 1-second delay!
    {{"commands": [{{"action": "turn_on", "device": "lights", "room": "living room"}}, {{"action": "turn_on", "device": "lights", "room": "kitchen"}}, {{"action": "turn_on", "device": "lights", "room": "bedroom"}}], "repeat": 1, "delay_ms": 1000}}

    General Query Examples:
    Command: What is the capital of France?
    Response: Well, hello there! The capital of France is Paris, a truly lovely city!

    Command: Tell me a fun fact.
    Response: Why certainly! Did you know that honey never spoils? How neat is that!

    Current Command: {command}
    Response:
    """
    try:
        response = client.models.generate_content(
            model="gemma-3-27b-it",
            contents=prompt
        )
        raw_model_output = response.text
        parsed_action_details = None
        try:
            start = raw_model_output.find('{')
            end = raw_model_output.rfind('}') + 1
            if start != -1 and end > start:
                json_str = raw_model_output[start:end]
                json_obj = json.loads(json_str)
                if isinstance(json_obj.get("commands"), list) and \
                   json_obj.get("commands") and \
                   json_obj.get("repeat") is not None:
                    valid_commands = True
                    for cmd in json_obj["commands"]:
                        if not (isinstance(cmd, dict) and
                                isinstance(cmd.get("action"), str) and
                                isinstance(cmd.get("device"), str) and
                                isinstance(cmd.get("room"), str)):
                            valid_commands = False
                            break
                    if valid_commands and \
                       (isinstance(json_obj["repeat"], int) or json_obj["repeat"] == "infinite") and \
                       (json_obj.get("delay_ms") is None or isinstance(json_obj.get("delay_ms"), int)):
                        parsed_action_details = json_obj

        except (json.JSONDecodeError, ValueError, TypeError) as e:
            print(f"Error parsing JSON from model output: {e}. JSON string was: '{json_str if 'json_str' in locals() else 'not found'}'")
        if parsed_action_details:
            return {
                "raw_response": raw_model_output, 
                "action_details": parsed_action_details
            }
        else:
            return {"raw_response": raw_model_output}

    except Exception as e:
        print(f"Error during model generation: {e}")
        return {"raw_response": f"Error generating response: {e}", "error": str(e)}
