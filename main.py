from fastapi import FastAPI, UploadFile, File
import uvicorn

app = FastAPI(
    title="Traffic Sentinel API",
    description="Real-time Traffic Inference API optimized with ONNX",
    version="2.0"
)

# Health check
@app.get("/")
def home():
    return {"status": "Online", "module": "Traffic Sentinel", "optimization": "ONNX Enabled"}

# Log event
@app.post("/log_event")
async def log_event(camera_id: str, detection_count: int):
    """
    Logs an event when the Client sees a car.
    """
    print(f"ALERT: Camera {camera_id} detected {detection_count} vehicles.")
    return {"message": "Event Logged", "status": "success"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)