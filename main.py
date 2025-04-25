from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import fitz  # PyMuPDF
import io
import base64
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB setup
MONGO_URI = os.getenv("MONGO_URI")
client = AsyncIOMotorClient(MONGO_URI)
db = client["fillandsign"]
documents_collection = db["documents"]

# Check MongoDB connection
try:
    client.admin.command('ping')
    print("Pinged MongoDB successfully!")
except Exception as e:
    print("MongoDB connection failed:", e)

# Pydantic Models
class Document(BaseModel):
    filename: str
    content: str  # Base64-encoded PDF

class SignRequest(BaseModel):
    filename: str
    signature: str  # Base64-encoded signature image
    x: float
    y: float
    width: float = 200  # Default width
    height: float = 100  # Default height
    page: int = 0  # Default to first page

# Upload PDF
@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    contents = await file.read()
    encoded_pdf = base64.b64encode(contents).decode("utf-8")
    await documents_collection.insert_one({"filename": file.filename, "content": encoded_pdf})
    return {"message": "PDF uploaded successfully", "filename": file.filename}

# Fetch PDF by filename
@app.get("/pdf/{filename}")
async def get_pdf(filename: str):
    document = await documents_collection.find_one({"filename": filename})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"filename": document["filename"], "content": document["content"]}

# Apply Signature at Specific Position
@app.post("/sign")
async def sign_pdf(sign_data: SignRequest):
    document = await documents_collection.find_one({"filename": sign_data.filename})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Decode the PDF and Signature
    pdf_data = base64.b64decode(document["content"])
    signature_image = base64.b64decode(sign_data.signature)

    # Open the PDF and target the page
    pdf = fitz.open(stream=pdf_data, filetype="pdf")
    if sign_data.page >= len(pdf):
        raise HTTPException(status_code=400, detail="Page number out of range")

    page = pdf[sign_data.page]

    # Insert signature
    rect = fitz.Rect(
        sign_data.x,
        sign_data.y,
        sign_data.x + sign_data.width,
        sign_data.y + sign_data.height
    )
    page.insert_image(rect, stream=signature_image)

    # Save updated PDF
    output_stream = io.BytesIO()
    pdf.save(output_stream)
    pdf.close()

    updated_pdf_encoded = base64.b64encode(output_stream.getvalue()).decode("utf-8")
    await documents_collection.update_one(
        {"filename": sign_data.filename},
        {"$set": {"content": updated_pdf_encoded}}
    )

    return {"message": "Signature added successfully", "filename": sign_data.filename}

# Download PDF
@app.get("/download/{filename}")
async def download_pdf(filename: str):
    document = await documents_collection.find_one({"filename": filename})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    pdf_data = base64.b64decode(document["content"])
    return Response(
        content=pdf_data,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
