"""
Stub Deepseek-R1 model server for local development.
Returns mock predictions without actual model inference.
"""

import time
import random
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict

app = FastAPI(title="Sentrix Model Server (Stub)")


class InferRequest(BaseModel):
    features: Dict
    max_tokens: int = 256


class InferResponse(BaseModel):
    score: float
    verdict: str
    explanation: str
    model_version: str
    latency_ms: float


@app.post("/v1/infer", response_model=InferResponse)
async def infer(request: InferRequest):
    """
    Mock inference endpoint.
    Returns random predictions for development/testing.
    """
    start_time = time.time()

    # Simulate inference delay (5-20ms)
    await asyncio.sleep(random.uniform(0.005, 0.020))

    # Generate mock score
    score = random.uniform(0.0, 1.0)

    # Determine verdict
    if score < 0.3:
        verdict = "benign"
        explanation = "Request appears normal with no suspicious patterns detected."
    elif score < 0.7:
        verdict = "suspicious"
        explanation = "Request shows some anomalous behavior that warrants investigation."
    else:
        verdict = "malicious"
        explanation = "Request exhibits clear attack patterns (SQL injection, XSS, etc.)."

    latency = (time.time() - start_time) * 1000

    return InferResponse(
        score=round(score, 2),
        verdict=verdict,
        explanation=explanation,
        model_version="r1-stub-v1",
        latency_ms=round(latency, 2)
    )


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "model": "r1-stub-v1"}


if __name__ == "__main__":
    import uvicorn
    import asyncio
    uvicorn.run(app, host="0.0.0.0", port=8001)
