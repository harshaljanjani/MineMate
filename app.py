from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from gemma_model import generate_response as gemma_generate_response, MAX_HISTORY_TURNS
from collections import deque

app = FastAPI(title="Gemma API")
conversation_history = deque(maxlen=MAX_HISTORY_TURNS)

class CommandRequest(BaseModel):
    command: str

@app.post("/generate")
async def generate_text(request: CommandRequest):
    current_history_list = list(conversation_history)
    response_data = gemma_generate_response(request.command, history=current_history_list)
    if response_data is None or "raw_response" not in response_data:
        print(f"Error: Gemma model returned invalid structure for command: {request.command}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate a valid response structure from the Gemma model"
        )
    if "error" not in response_data:
        conversation_history.append((request.command, response_data["raw_response"]))
    return response_data

# Utility endpoints.
@app.get("/history")
async def get_history():
    return {"history": list(conversation_history)}

@app.post("/clear_history")
async def clear_history_endpoint():
    conversation_history.clear()
    return {"message": "Conversation history cleared."}