"""
AI Orchestrator - Orquesta las decisiones de IA para ejecutar acciones en la app móvil.

NOTA: Este archivo mantiene compatibilidad hacia atrás.
Para nueva funcionalidad, usar src.v1.ai_orchestrator (QAI V1) o src.v2.ai_orchestrator (QAI V2).
"""

from src.v1.ai_orchestrator import (
    QAIV1Orchestrator as AIOrchestrator,
    StepContext,
    APP_STATE_NAMES,
)

# Alias para compatibilidad hacia atrás
__all__ = ['AIOrchestrator', 'StepContext', 'APP_STATE_NAMES']
