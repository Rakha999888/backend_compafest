import csv
import io
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.file_validator import FileValidator, FileValidationError
from app.services.validation_service import ValidationService
from app.services.ml.preprocessor import DataPreprocessor

router = APIRouter(prefix="/recommend", tags=["Upload"])

preprocessor = DataPreprocessor()

@router.post("/upload")
async def upload_recommendation(file: UploadFile = File(...)):
    content = await file.read()
    file_size = len(content)
    
    try:
        FileValidator.validate(
            filename=file.filename or "unknown",
            content_type=file.content_type,
            size=file_size
        )
    except FileValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    
    ext = ""
    if file.filename:
        dot_idx = file.filename.rfind(".")
        if dot_idx != -1 :
            ext = file.filename[dot_idx:].lower()
            
    if ext == ".csv":
        raw_text = content.decode("utf-8")
        reader = csv.reader(io.StringIO(raw_text))
        columns = next(reader, [])

        col_errors = ValidationService.validate_csv_columns(columns)
        if col_errors:
            raise HTTPException(status_code=422, detail=col_errors)

        result = preprocessor.preprocess_csv(raw_text)
    elif ext == ".xlsx":
        raise HTTPException(status_code=501, detail="XLSX support not yet implemented")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    return {
        "success": True,
        "message": "File uploaded and parsed successfully",
        "filename": file.filename,
        "rows": result.total_transactions,
        "unique_products": len(result.unique_products),
    }