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

def generate_response(command):
    if not client:
        return {"raw_response": "GenAI client not initialized.", "error": "Client not initialized"}

    prompt = f"""You are a friendly and slightly jovial smart home assistant.
    Given a command, determine if it's a smart home instruction or a general query.

    If it's a smart home instruction:
    1. Provide a short, friendly, conversational acknowledgement.
    2. On a NEW LINE, provide a JSON object containing "action", "device", and "room".
    Valid actions: turn_on, turn_off, lock, unlock, open, close.
    Valid rooms: living room, kitchen, bedroom, bathroom, office, main.

    If it's a general query, provide a conversational answer with a warm and slightly jovial tone.
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

    Command: {command}
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
