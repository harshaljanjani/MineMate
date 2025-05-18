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
    for i, (user_cmd, assistant_resp) in enumerate(history):
        conversational_resp = assistant_resp
        json_start = assistant_resp.find('{')
        if json_start != -1:
            pre_json_text = assistant_resp[:json_start].strip()
            if pre_json_text:
                conversational_resp = pre_json_text
        formatted_history_parts.append(f"Previous User: {user_cmd}\nPrevious Assistant: {conversational_resp}")
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
    2. On a NEW LINE, provide a JSON object containing "action", "device", and "room".
    Valid actions: turn_on, turn_off, lock, unlock, open, close.
    Valid rooms: living room, kitchen, bedroom, bathroom, office, main.

    If it's a general query, provide a conversational answer with a warm and slightly jovial tone, considering the history for context.
    Format your entire response clearly for display in a terminal.

    Smart Home Examples:
    Command: Turn on the lights in the kitchen.
    Response:
    Okay, I'll get those kitchen lights for you!
    {{"action": "turn_on", "device": "lights", "room": "kitchen"}}

    Command: Lock the main door.
    Response:
    You got it! Locking the main door now.
    {{"action": "lock", "device": "door", "room": "main"}}

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
                required_fields = {"action", "device", "room"}
                if all(field in json_obj and isinstance(json_obj[field], str) for field in required_fields):
                    parsed_action_details = {
                        "action": json_obj["action"],
                        "device": json_obj["device"],
                        "room": json_obj["room"]
                    }
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
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
