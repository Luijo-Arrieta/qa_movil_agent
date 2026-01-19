"""
Middleware Result - Tipo de dato estructurado para respuestas del middleware.

Este módulo define el tipo de dato que todos los middlewares deben retornar
para mantener consistencia en el manejo de respuestas (permitido/denegado/error).
"""

from dataclasses import dataclass
from typing import Optional, List, Any
from enum import Enum


class MiddlewareStatus(Enum):
    """Estado de la validación del middleware."""
    ALLOWED = "allowed"  # Acción permitida, continuar normalmente
    DENIED = "denied"    # Acción denegada por scope
    ERROR = "error"      # Error técnico (no relacionado con scope)


@dataclass
class MiddlewareResult:
    """
    Resultado tipado de validación del middleware.
    
    Este tipo de dato debe ser retornado por todos los middlewares
    cuando una acción es denegada o hay un error. Cuando la acción
    es permitida, los métodos pueden retornar el resultado normal
    (ej: List[UIElement] o str).
    
    Attributes:
        status: Estado de la validación (ALLOWED, DENIED, ERROR)
        message: Mensaje claro para el agente
        allowed_apps: Lista de apps permitidas (si aplica)
        suggested_tool: Herramienta sugerida (ej: "activate_app")
        data: Datos adicionales (ej: elementos UI parseados)
    """
    status: MiddlewareStatus
    message: str  # Mensaje claro para el agente
    allowed_apps: Optional[List[str]] = None  # Lista de apps permitidas (si aplica)
    suggested_tool: Optional[str] = None  # Herramienta sugerida (ej: "activate_app")
    data: Optional[Any] = None  # Datos adicionales (ej: elementos UI parseados)
    
    def is_allowed(self) -> bool:
        """Retorna True si la acción está permitida."""
        return self.status == MiddlewareStatus.ALLOWED
    
    def is_denied(self) -> bool:
        """Retorna True si la acción fue denegada."""
        return self.status == MiddlewareStatus.DENIED
    
    def is_error(self) -> bool:
        """Retorna True si hubo un error técnico."""
        return self.status == MiddlewareStatus.ERROR
