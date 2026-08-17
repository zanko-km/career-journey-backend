from fastapi import FastAPI


app = FastAPI(
    title = "Career Journey API",
    version = "0.1.0"
)


@app.get("/health")
async def health_check():
    return {"status": "ok"}