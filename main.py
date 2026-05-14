from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import Binary
import fitz  # PyMuPDF
import io
import base64
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB

client = AsyncIOMotorClient(MONGO_URI)
db = client["fillandsign"]
documents_collection = db["documents"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    await client.admin.command("ping")
    print("MongoDB connected.")
    yield
    client.close()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SignRequest(BaseModel):
    filename: str
    signature: str  # Base64-encoded signature image
    x: float
    y: float
    width: float = 200
    height: float = 100
    page: int = 0


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 15 MB limit")
    await documents_collection.update_one(
        {"filename": file.filename},
        {"$set": {"filename": file.filename, "content": Binary(contents)}},
        upsert=True,
    )
    return {"message": "PDF uploaded successfully", "filename": file.filename}


@app.get("/pdf/{filename}")
async def get_pdf(filename: str):
    document = await documents_collection.find_one({"filename": filename})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    encoded = base64.b64encode(bytes(document["content"])).decode("utf-8")
    return {"filename": document["filename"], "content": encoded}


@app.post("/sign")
async def sign_pdf(sign_data: SignRequest):
    document = await documents_collection.find_one({"filename": sign_data.filename})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    pdf_data = bytes(document["content"])
    signature_image = base64.b64decode(sign_data.signature)

    pdf = fitz.open(stream=pdf_data, filetype="pdf")
    if sign_data.page >= len(pdf):
        raise HTTPException(status_code=400, detail="Page number out of range")

    page = pdf[sign_data.page]
    rect = fitz.Rect(
        sign_data.x,
        sign_data.y,
        sign_data.x + sign_data.width,
        sign_data.y + sign_data.height,
    )
    page.insert_image(rect, stream=signature_image)

    output_stream = io.BytesIO()
    pdf.save(output_stream)
    pdf.close()

    await documents_collection.update_one(
        {"filename": sign_data.filename},
        {"$set": {"content": Binary(output_stream.getvalue())}},
    )
    return {"message": "Signature added successfully", "filename": sign_data.filename}


@app.post("/convert-pdf-to-images")
async def convert_pdf_to_images(file: UploadFile):
    pdf_data = await file.read()
    doc = fitz.open(stream=pdf_data, filetype="pdf")

    first_page = doc[0]
    rect = first_page.rect
    dimensions = {"width": rect.width, "height": rect.height}

    images = []
    for page_num in range(doc.page_count):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_base64 = base64.b64encode(pix.tobytes("png")).decode()
        images.append(img_base64)

    doc.close()
    return {"images": images, "dimensions": dimensions}


@app.get("/download/{filename}")
async def download_pdf(filename: str):
    document = await documents_collection.find_one({"filename": filename})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return Response(
        content=bytes(document["content"]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
