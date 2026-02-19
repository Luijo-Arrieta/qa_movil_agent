"""
Endpoints para generar archivos de test.
"""

import logging
from fastapi import APIRouter, HTTPException
from backend.api.models.test import GenerateTestRequest
from backend.services.test_generator import TestGenerator

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/generate")
async def generate_test(request: GenerateTestRequest):
    """
    Genera un archivo de test Python desde una descripción.
    
    Returns:
        Ruta del archivo generado
    """
    try:
        file_path = TestGenerator.generate_test_file(
            description=request.description,
            test_name=request.test_name,
            output_path=request.output_path
        )
        
        return {
            "success": True,
            "file_path": file_path,
            "message": f"Archivo generado exitosamente: {file_path}"
        }
    except Exception as e:
        logger.error(f"Error generando test: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
