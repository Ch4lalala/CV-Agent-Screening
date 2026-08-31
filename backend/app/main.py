from fastapi import FastAPI

app = FastAPI(
    title="Evidence-Grounded Recruitment Agent API",
    version="0.1.0",
)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Report whether the API process is available."""
    return {"status": "healthy"}

