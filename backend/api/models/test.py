"""
Models para tests.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class TestPlanRequest(BaseModel):
    """Request para ejecutar un test plan."""
    test_plan: List[str] = Field(..., description="Lista de pasos del test en lenguaje natural")
    objective: Optional[str] = Field(None, description="Objetivo general del test")
    device_name: Optional[str] = Field(None, description="Nombre del dispositivo (opcional)")
    app_package: Optional[str] = Field(None, description="Package de la app Android")
    app_activity: Optional[str] = Field(None, description="Activity principal de la app")


class TestExecutionResponse(BaseModel):
    """Response de ejecución de test."""
    test_id: str = Field(..., description="ID único del test ejecutado")
    status: str = Field(..., description="Estado: running, completed, failed")
    message: str = Field(..., description="Mensaje descriptivo")
    created_at: datetime = Field(default_factory=datetime.now)


class TestResult(BaseModel):
    """Resultado completo de un test."""
    test_id: str
    status: str
    success: bool
    total_steps: int
    completed_steps: int
    failed_steps: int
    execution_time: float
    error_message: Optional[str] = None
    execution_stats: Optional[dict] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class GenerateTestRequest(BaseModel):
    """Request para generar un archivo de test."""
    description: str = Field(..., description="Descripción del test en lenguaje natural")
    test_name: Optional[str] = Field(None, description="Nombre del archivo de test")
    output_path: Optional[str] = Field(None, description="Ruta de salida (opcional)")
