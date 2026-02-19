"""
Endpoints para ejecutar tests.
"""

import logging
from fastapi import APIRouter, HTTPException
from backend.api.models.test import TestPlanRequest, TestExecutionResponse, TestResult
from backend.services.test_executor import TestExecutor

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/execute", response_model=TestExecutionResponse)
async def execute_test(request: TestPlanRequest):
    """
    Ejecuta un test plan.
    
    Returns:
        ID del test iniciado
    """
    try:
        test_id = TestExecutor.execute_test(
            test_plan=request.test_plan,
            objective=request.objective,
            device_name=request.device_name,
            app_package=request.app_package,
            app_activity=request.app_activity
        )
        
        return TestExecutionResponse(
            test_id=test_id,
            status="running",
            message="Test iniciado exitosamente"
        )
    except Exception as e:
        logger.error(f"Error ejecutando test: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
