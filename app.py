from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from gemma_model import generate_response as gemma_generate_response

app = FastAPI(title="Gemma API")

class CommandRequest(BaseModel):
    command: str

@app.post("/generate")
async def generate_text(request: CommandRequest):
    response_data = gemma_generate_response(request.command)
    if response_data is None or "raw_response" not in response_data:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate a valid response structure from the Gemma model"
        )
    return response_data