"""
Endpoints para obtener resultados de tests.
"""

import logging
from fastapi import APIRouter, HTTPException
from backend.api.models.test import TestResult
from backend.services.test_executor import TestExecutor

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{test_id}", response_model=TestResult)
async def get_result(test_id: str):
    """
    Obtiene el resultado de un test ejecutado.
    
    Args:
        test_id: ID del test
        
    Returns:
        Resultado del test
    """
    result = TestExecutor.get_result(test_id)
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Test {test_id} no encontrado")
    
    return TestResult(**result)
