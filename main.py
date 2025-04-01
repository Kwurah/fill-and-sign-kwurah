from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Response
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import fitz  # PyMuPDF
import io
import base64
import os
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Setup
MONGO_URI = os.getenv("MONGO_URI")
client = AsyncIOMotorClient(MONGO_URI)
db = client["fillandsign"]
documents_collection = db["documents"]

try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

# Model for storing documents
class Document(BaseModel):
    filename: str
    content: str  # Base64 encoded PDF

class SignRequest(BaseModel):
    filename: str
    signature: str  # Base64 encoded image

# Upload PDF endpoint
@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    contents = await file.read()
    encoded_pdf = base64.b64encode(contents).decode("utf-8")
    document_data = {"filename": file.filename, "content": encoded_pdf}
    await documents_collection.insert_one(document_data)
    return {"message": "PDF uploaded successfully", "filename": file.filename}

# Fetch PDF endpoint
@app.get("/pdf/{filename}")
async def get_pdf(filename: str):
    document = await documents_collection.find_one({"filename": filename})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"filename": document["filename"], "content": document["content"]}

# Add Signature endpoint (Fixed)
@app.post("/sign")
async def add_signature(sign_data: SignRequest):
    filename = sign_data.filename
    signature = sign_data.signature

    document = await documents_collection.find_one({"filename": filename})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    pdf_data = base64.b64decode(document["content"])
    signature_data = base64.b64decode(signature)

    pdf_doc = fitz.open(stream=pdf_data, filetype="pdf")
    page = pdf_doc[0]  # Assume signature goes on the first page
    
    rect = fitz.Rect(100, 100, 300, 200)  # Adjust signature position
    page.insert_image(rect, stream=signature_data)
    
    pdf_stream = io.BytesIO()
    pdf_doc.save(pdf_stream)
    pdf_doc.close()
    
    updated_pdf_encoded = base64.b64encode(pdf_stream.getvalue()).decode("utf-8")
    await documents_collection.update_one(
        {"filename": filename},
        {"$set": {"content": updated_pdf_encoded}}
    )
    
    return {"message": "Signature added successfully", "filename": filename}

# Download PDF endpoint
@app.get("/download/{filename}")
async def download_pdf(filename: str):
    document = await documents_collection.find_one({"filename": filename})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    pdf_data = base64.b64decode(document["content"])
    return Response(content=pdf_data, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={filename}"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)