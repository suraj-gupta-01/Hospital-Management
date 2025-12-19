from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from google.cloud import vision
from PIL import Image
import io
import base64
import json
try:
    import google.generativeai as genai
except Exception:
    genai = None


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI(title="Prescription OCR API")
api_router = APIRouter(prefix="/api")

# Initialize Google Vision client (will be initialized when first used)
vision_client = None

def get_vision_client():
    global vision_client
    if vision_client is None:
        google_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if google_creds and os.path.exists(google_creds):
            vision_client = vision.ImageAnnotatorClient()
        else:
            # No credentials available, will use mock
            vision_client = None
    return vision_client

# Pydantic Models
class PrescriptionData(BaseModel):
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None
    symptoms: Optional[str] = None
    prescription: Optional[str] = None
    dosage: Optional[str] = None
    doctor_notes: Optional[str] = None

class PrescriptionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    filename: str
    upload_timestamp: str
    processing_status: str
    raw_text: Optional[str] = None
    structured_data: Optional[PrescriptionData] = None
    suggested_data: Optional[PrescriptionData] = None
    error_message: Optional[str] = None

async def process_ocr(image_bytes: bytes) -> dict:
    """Process image through OCR"""
    try:
        client = get_vision_client()
        if client is None:
            # Mock OCR response for demo
            return {
                "success": True,
                "text": "Dr. John Smith\nPatient: Jane Doe\nSymptoms: Fever, cough\nPrescription: Amoxicillin 500mg\nDosage: 3 times daily for 7 days\nNotes: Take with food"
            }
        
        # Real OCR processing
        image = vision.Image(content=image_bytes)
        response = client.document_text_detection(image=image)
        
        if response.error.message:
            return {"success": False, "error": response.error.message}
        
        text = response.full_text_annotation.text if response.full_text_annotation else ""
        return {"success": True, "text": text}
    except Exception as e:
        logging.error(f"OCR error: {str(e)}")
        return {"success": False, "error": str(e)}

async def extract_structured_data(raw_text: str) -> dict:
    """Use Gemini to extract structured data from OCR text"""
    try:
        gemini_key = os.getenv("GEMINI_API_KEY")
        gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

        # If no key or genai library unavailable, return mock response
        if not gemini_key or genai is None:
            return {
                "success": True,
                "data": {
                    "patient_name": "Jane Doe",
                    "doctor_name": "Dr. John Smith",
                    "symptoms": "Fever, cough",
                    "prescription": "Amoxicillin 500mg",
                    "dosage": "3 times daily for 7 days",
                    "doctor_notes": "Take with food"
                }
            }

        # System prompt (configurable via env)
        gemini_system_prompt = os.getenv(
            "GEMINI_SYSTEM_PROMPT",
            "You are an AI that extracts structured data from medical prescriptions. Extract patient_name, doctor_name, symptoms, prescription (medicine names), dosage, and doctor_notes from the text. Return ONLY a valid JSON object with these fields. If a field is not found, use null. Return only JSON, no explanation, no markdown.",
        )

        # Build instruction
        instruction = f"""Extract structured data from this prescription text and return ONLY a JSON object:

{raw_text}

Return format:
{{
  "patient_name": "...",
  "doctor_name": "...",
  "symptoms": "...",
  "prescription": "...",
  "dosage": "...",
  "doctor_notes": "..."
}}
"""

        # Combine system prompt and instruction
        prompt = gemini_system_prompt + "\n\n" + instruction
        prompt = f"""Extract structured data from this prescription text and return ONLY a JSON object:

{raw_text}

Return format:
{{
  "patient_name": "...",
  "doctor_name": "...",
  "symptoms": "...",
  "prescription": "...",
  "dosage": "...",
  "doctor_notes": "..."
}}
"""

        # Call Gemini via google.generativeai (best-effort across versions)
        try:
            genai.configure(api_key=gemini_key)

            response_text = ""
            try:
                resp = genai.generate_text(model=gemini_model, prompt=prompt)
                if hasattr(resp, "text") and resp.text:
                    response_text = resp.text
                elif isinstance(resp, dict):
                    if "candidates" in resp and resp["candidates"]:
                        response_text = resp["candidates"][0].get("content", "")
                    elif "output" in resp and isinstance(resp["output"], list) and resp["output"]:
                        response_text = resp["output"][0].get("content", "")
                    else:
                        response_text = str(resp)
                else:
                    response_text = str(resp)
            except Exception:
                # fallback to chat-style call
                resp = genai.chat.create(model=gemini_model, messages=[{"role": "user", "content": prompt}])
                if isinstance(resp, dict):
                    if "candidates" in resp and resp["candidates"]:
                        response_text = resp["candidates"][0].get("content", "")
                    elif "output" in resp and isinstance(resp["output"], list) and resp["output"]:
                        first = resp["output"][0]
                        response_text = first.get("content", "") if isinstance(first, dict) else str(first)
                    elif "choices" in resp and resp["choices"]:
                        response_text = resp["choices"][0].get("message", {}).get("content", "")
                    else:
                        response_text = str(resp)

            # Normalize and strip markdown/code fences
            response_text = response_text.strip()
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            data = json.loads(response_text)
            return {"success": True, "data": data}
        except json.JSONDecodeError as e:
            logging.error(f"JSON parsing error: {str(e)}")
            return {"success": False, "error": "Invalid JSON returned by Gemini"}
        except Exception as e:
            logging.error(f"Gemini extraction error: {str(e)}")
            return {"success": False, "error": str(e)}
    except Exception as e:
        logging.error(f"LLM extraction error: {str(e)}")
        return {"success": False, "error": str(e)}

async def process_prescription_background(prescription_id: str, image_bytes: bytes):
    """Background task to process prescription"""
    try:
        # Update status to processing
        await db.prescriptions.update_one(
            {"id": prescription_id},
            {"$set": {"processing_status": "processing"}}
        )
        
        # Run OCR
        ocr_result = await process_ocr(image_bytes)
        if not ocr_result["success"]:
            await db.prescriptions.update_one(
                {"id": prescription_id},
                {"$set": {
                    "processing_status": "failed",
                    "error_message": ocr_result.get("error", "OCR failed")
                }}
            )
            return
        
        raw_text = ocr_result["text"]
        
        # Extract structured data
        extraction_result = await extract_structured_data(raw_text)
        if not extraction_result["success"]:
            await db.prescriptions.update_one(
                {"id": prescription_id},
                {"$set": {
                    "processing_status": "completed",
                    "raw_text": raw_text,
                    "error_message": f"Extraction failed: {extraction_result.get('error')}"
                }}
            )
            return
        
        # Stage suggested data and move to awaiting_verification
        await db.prescriptions.update_one(
            {"id": prescription_id},
            {"$set": {
                "processing_status": "awaiting_verification",
                "raw_text": raw_text,
                "suggested_data": extraction_result["data"]
            }}
        )
    except Exception as e:
        logging.error(f"Background processing error: {str(e)}")
        await db.prescriptions.update_one(
            {"id": prescription_id},
            {"$set": {
                "processing_status": "failed",
                "error_message": str(e)
            }}
        )

@api_router.post("/upload-prescription")
async def upload_prescription(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Upload a prescription image for OCR processing"""
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read file
        contents = await file.read()
        
        # Validate image size (20 MB limit)
        if len(contents) > 20 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image size must be less than 20 MB")
        
        # Create prescription record
        prescription_id = str(uuid.uuid4())
        prescription_doc = {
            "id": prescription_id,
            "filename": file.filename,
            "upload_timestamp": datetime.now(timezone.utc).isoformat(),
            "processing_status": "pending",
            "raw_text": None,
            "structured_data": None,
            "error_message": None
        }
        
        await db.prescriptions.insert_one(prescription_doc)
        
        # Schedule background processing
        background_tasks.add_task(process_prescription_background, prescription_id, contents)
        
        return {
            "id": prescription_id,
            "status": "pending",
            "message": "Prescription uploaded and queued for processing"
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/prescriptions/{prescription_id}", response_model=PrescriptionResponse)
async def get_prescription(prescription_id: str):
    """Get prescription by ID"""
    try:
        prescription = await db.prescriptions.find_one({"id": prescription_id}, {"_id": 0})
        if not prescription:
            raise HTTPException(status_code=404, detail="Prescription not found")
        return prescription
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Get prescription error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/prescriptions", response_model=List[PrescriptionResponse])
async def get_all_prescriptions(limit: int = 50):
    """Get all prescriptions"""
    try:
        prescriptions = await db.prescriptions.find(
            {}, {"_id": 0}
        ).sort("upload_timestamp", -1).limit(limit).to_list(limit)
        return prescriptions
    except Exception as e:
        logging.error(f"Get prescriptions error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/prescriptions/{prescription_id}/verify")
async def verify_prescription(prescription_id: str, data: PrescriptionData):
    """Finalize and store verified structured data provided by a human reviewer"""
    try:
        update_doc = {
            "structured_data": data.dict(),
            "processing_status": "verified",
            "verified_timestamp": datetime.now(timezone.utc).isoformat(),
            "suggested_data": None
        }

        result = await db.prescriptions.update_one({"id": prescription_id}, {"$set": update_doc})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Prescription not found")

        prescription = await db.prescriptions.find_one({"id": prescription_id}, {"_id": 0})
        return prescription
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Verify prescription error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/")
async def root():
    return {"message": "Prescription OCR API"}

# Include router
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
