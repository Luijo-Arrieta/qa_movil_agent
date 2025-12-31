"""
Test Runner - Orquesta la ejecución de pruebas usando el agente de IA.
"""

import time
import logging
from typing import List, Optional
from appium.webdriver import Remote

from src.ui_parser import UIParser
from src.agent_tools import AppiumSkills
from src.ai_orchestrator import AIOrchestrator

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AITestRunner:
    """
    Ejecutor de pruebas que orquesta el flujo completo:
    1. Obtiene XML del driver
    2. UIParser parsea y genera JSON
    3. AI Orchestrator decide acción
    4. Agent Tools ejecuta acción
    """

    def __init__(self, driver: Remote, objective: Optional[str] = None):
        """
        Inicializa el test runner.

        Args:
            driver: Instancia del driver de Appium
            objective: Objetivo general del test (opcional)
        """
        self.driver = driver
        self.objective = objective
        self.ui_parser = UIParser()
        self.agent_tools = AppiumSkills(driver, self.ui_parser)
        self.ai_orchestrator = AIOrchestrator()
        self.action_history: List[str] = []
        self.max_retries = 3

    def run_test_plan(self, test_plan: List[str]) -> bool:
        """
        Ejecuta un plan de prueba con pasos en lenguaje natural.

        Args:
            test_plan: Lista de pasos a ejecutar en lenguaje natural

        Returns:
            True si todos los pasos se completaron exitosamente, False en caso contrario
        """
        logger.info(f"Iniciando ejecución de plan de prueba con {len(test_plan)} pasos")
        if self.objective:
            logger.info(f"Objetivo general: {self.objective}")

        for step_index, step in enumerate(test_plan, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"Paso {step_index}/{len(test_plan)}: {step}")
            logger.info(f"{'='*60}")

            success = self._execute_step(step, step_index)

            if not success:
                logger.error(f"❌ Fallo en paso {step_index}: {step}")
                return False

            logger.info(f"✓ Paso {step_index} completado exitosamente\n")

        logger.info("✅ Todos los pasos se completaron exitosamente")
        return True

    def _execute_step(self, step: str, step_index: int) -> bool:
        """
        Ejecuta un paso individual con sistema de reintentos.

        Args:
            step: Descripción del paso en lenguaje natural
            step_index: Índice del paso (para logging)

        Returns:
            True si el paso se completó exitosamente, False en caso contrario
        """
        for attempt in range(1, self.max_retries + 1):
            logger.info(f"Intento {attempt}/{self.max_retries} para paso {step_index}")

            try:
                # Paso 1: Obtener XML del driver
                logger.debug("Obteniendo XML de la pantalla...")
                xml_source = self.agent_tools.get_screen_tree()

                # Paso 2: UIParser parsea XML y genera JSON
                logger.debug("Parseando UI...")
                ui_elements = self.ui_parser.parse_screen(xml_source)
                logger.info(f"Elementos encontrados: {len(ui_elements)}")

                # Paso 3: AI Orchestrator decide acción
                logger.debug("Consultando IA para decidir acción...")
                ai_decision = self.ai_orchestrator.decide_next_action(
                    ui_elements=ui_elements,
                    current_step=step,
                    action_history=self.action_history[-5:],  # Últimas 5 acciones
                    objective=self.objective,
                )

                # Paso 4-7: Ejecutar acción(es) decidida(s) por la IA
                if ai_decision.get("tool_calls"):
                    success = self._execute_tool_calls(ai_decision["tool_calls"], step)
                    if success:
                        # Agregar a historial
                        action_summary = f"Paso: {step}, Acciones: {len(ai_decision['tool_calls'])}"
                        self.action_history.append(action_summary)
                        return True
                else:
                    # La IA indica que no se requiere acción o el paso se cumplió
                    logger.info(f"IA indica: {ai_decision.get('message', 'No se requiere acción')}")
                    action_summary = f"Paso: {step}, Estado: {ai_decision.get('message', 'Completado')}"
                    self.action_history.append(action_summary)
                    return True

                # Si llegamos aquí, la acción no fue exitosa
                logger.warning(f"⚠️ Intento {attempt} falló, reintentando...")
                time.sleep(2)  # Esperar antes de reintentar

            except Exception as e:
                logger.error(f"Error en intento {attempt}: {str(e)}")
                if attempt < self.max_retries:
                    time.sleep(2)
                    continue
                else:
                    return False

        return False

    def _execute_tool_calls(self, tool_calls: List[dict], step: str) -> bool:
        """
        Ejecuta las llamadas a herramientas decididas por la IA.

        Args:
            tool_calls: Lista de tool calls de la IA
            step: Paso actual (para contexto)

        Returns:
            True si todas las acciones se ejecutaron exitosamente
        """
        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["arguments"]

            logger.info(f"🤖 Ejecutando: {tool_name}({tool_args})")

            try:
                result = None

                if tool_name == "touch_element_by_id":
                    element_id = tool_args["element_id"]
                    result = self.agent_tools.touch_element_by_id(element_id)

                elif tool_name == "fill_field_by_id":
                    element_id = tool_args["element_id"]
                    value = tool_args["value"]
                    result = self.agent_tools.fill_field_by_id(element_id, value)

                elif tool_name == "scroll":
                    direction = tool_args["direction"]
                    result = self.agent_tools.scroll(direction)

                elif tool_name == "go_back":
                    result = self.agent_tools.go_back()

                elif tool_name == "assert_screen_contains":
                    text = tool_args["text"]
                    is_present, message = self.agent_tools.assert_screen_contains(text)
                    result = message
                    if not is_present:
                        logger.error(f"❌ Aserción falló: {message}")
                        return False

                else:
                    logger.warning(f"⚠️ Herramienta desconocida: {tool_name}")
                    continue

                # Verificar resultado
                if result and "Error" in result:
                    logger.error(f"❌ {result}")
                    return False
                elif result:
                    logger.info(f"✓ {result}")

                # Esperar un momento para que la UI se actualice
                time.sleep(1)

            except Exception as e:
                logger.error(f"❌ Error ejecutando {tool_name}: {str(e)}")
                return False

        return True

    def clear_history(self):
        """Limpia el historial de acciones."""
        self.action_history = []

