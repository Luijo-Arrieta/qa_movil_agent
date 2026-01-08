"""
Test Runner - Orquesta la ejecución de pruebas usando el agente de IA.
"""

import time
import logging
import traceback
from typing import List, Optional
from datetime import datetime
from appium.webdriver import Remote

from src.ui_parser import UIParser
from src.agent_tools import AppiumSkills
from src.ai_orchestrator import AIOrchestrator
from src.config import Config

# Configurar logging con formato detallado
logging.basicConfig(
    level=logging.DEBUG,  # Cambiado a DEBUG para máxima visibilidad
    format='%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
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
        logger.info("=" * 80)
        logger.info("TEST_RUNNER: Inicializando AITestRunner")
        logger.info("=" * 80)
        
        self._start_time = datetime.now()
        
        # Debug: Imprimir configuración actual
        logger.info("TEST_RUNNER: Imprimiendo configuración...")
        Config.debug_print_config()
        
        # Validar configuración
        logger.info("TEST_RUNNER: Validando configuración...")
        is_valid, error_msg = Config.validate()
        if not is_valid:
            logger.error(f"TEST_RUNNER ERROR: Configuración inválida: {error_msg}")
            raise ValueError(f"Configuración inválida: {error_msg}")
        logger.info("TEST_RUNNER: ✓ Configuración válida")
        
        self.driver = driver
        self.objective = objective
        
        # Verificar driver
        logger.debug("TEST_RUNNER: Verificando driver de Appium...")
        try:
            session_id = driver.session_id
            logger.info(f"TEST_RUNNER: ✓ Driver activo - Session ID: {session_id}")
        except Exception as e:
            logger.error(f"TEST_RUNNER ERROR: Driver no disponible: {e}")
            raise
        
        # Inicializar componentes
        logger.info("TEST_RUNNER: Inicializando componentes...")
        
        logger.debug("TEST_RUNNER: Creando UIParser...")
        self.ui_parser = UIParser()
        logger.debug("TEST_RUNNER: ✓ UIParser creado")
        
        logger.debug("TEST_RUNNER: Creando AppiumSkills...")
        self.agent_tools = AppiumSkills(driver, self.ui_parser)
        logger.debug("TEST_RUNNER: ✓ AppiumSkills creado")
        
        logger.debug("TEST_RUNNER: Creando AIOrchestrator...")
        self.ai_orchestrator = AIOrchestrator()
        logger.debug("TEST_RUNNER: ✓ AIOrchestrator creado")
        
        self.action_history: List[str] = []
        self.max_retries = 3
        
        # Estadísticas de ejecución
        self._execution_stats = {
            "total_steps": 0,
            "completed_steps": 0,
            "failed_steps": 0,
            "total_actions": 0,
            "total_ai_calls": 0,
            "start_time": self._start_time.isoformat(),
        }
        
        logger.info(f"TEST_RUNNER: ✓ Inicialización completa")
        if self.objective:
            logger.info(f"TEST_RUNNER: Objetivo del test: '{self.objective}'")

    def run_test_plan(self, test_plan: List[str]) -> bool:
        """
        Ejecuta un plan de prueba con pasos en lenguaje natural.

        Args:
            test_plan: Lista de pasos a ejecutar en lenguaje natural

        Returns:
            True si todos los pasos se completaron exitosamente, False en caso contrario
        """
        logger.info("")
        logger.info("█" * 80)
        logger.info("█  TEST_RUNNER: INICIANDO EJECUCIÓN DE PLAN DE PRUEBA")
        logger.info("█" * 80)
        logger.info("")
        
        plan_start_time = datetime.now()
        self._execution_stats["total_steps"] = len(test_plan)
        
        logger.info(f"TEST_RUNNER: Total de pasos en el plan: {len(test_plan)}")
        logger.info(f"TEST_RUNNER: Max reintentos por paso: {self.max_retries}")
        if self.objective:
            logger.info(f"TEST_RUNNER: Objetivo general: '{self.objective}'")
        
        # Listar todos los pasos
        logger.info("TEST_RUNNER: Plan de prueba:")
        for idx, step in enumerate(test_plan, 1):
            logger.info(f"  {idx}. {step}")
        logger.info("")

        for step_index, step in enumerate(test_plan, 1):
            step_start_time = datetime.now()
            
            logger.info("")
            logger.info("═" * 80)
            logger.info(f"▶ PASO {step_index}/{len(test_plan)}: {step}")
            logger.info("═" * 80)
            logger.info(f"TEST_RUNNER: Iniciando paso {step_index} a las {step_start_time.strftime('%H:%M:%S.%f')[:-3]}")

            success = self._execute_step(step, step_index)
            
            step_elapsed = (datetime.now() - step_start_time).total_seconds()

            if not success:
                self._execution_stats["failed_steps"] += 1
                logger.error("")
                logger.error("╔" + "═" * 78 + "╗")
                logger.error(f"║ ❌ FALLO EN PASO {step_index}: {step[:60]}")
                logger.error("╚" + "═" * 78 + "╝")
                logger.error(f"TEST_RUNNER: Tiempo transcurrido en paso fallido: {step_elapsed:.2f}s")
                
                # DEBUG: Dump del estado del UIParser para diagnóstico
                logger.error("TEST_RUNNER: Dumping estado del UIParser para diagnóstico...")
                self.ui_parser.debug_dump_element_map(log_output=True)
                
                # Imprimir resumen de estadísticas
                self._print_execution_summary(plan_start_time)
                return False

            self._execution_stats["completed_steps"] += 1
            logger.info("")
            logger.info(f"✅ PASO {step_index} COMPLETADO en {step_elapsed:.2f}s")
            logger.info("")

        # Plan completado exitosamente
        plan_elapsed = (datetime.now() - plan_start_time).total_seconds()
        
        logger.info("")
        logger.info("█" * 80)
        logger.info("█  ✅ PLAN DE PRUEBA COMPLETADO EXITOSAMENTE")
        logger.info("█" * 80)
        logger.info(f"TEST_RUNNER: Tiempo total de ejecución: {plan_elapsed:.2f}s")
        
        self._print_execution_summary(plan_start_time)
        return True
    
    def _print_execution_summary(self, start_time: datetime) -> None:
        """Imprime un resumen de la ejecución."""
        elapsed = (datetime.now() - start_time).total_seconds()
        
        logger.info("")
        logger.info("┌" + "─" * 50 + "┐")
        logger.info("│  RESUMEN DE EJECUCIÓN")
        logger.info("├" + "─" * 50 + "┤")
        logger.info(f"│  Tiempo total: {elapsed:.2f}s")
        logger.info(f"│  Pasos totales: {self._execution_stats['total_steps']}")
        logger.info(f"│  Pasos completados: {self._execution_stats['completed_steps']}")
        logger.info(f"│  Pasos fallidos: {self._execution_stats['failed_steps']}")
        logger.info(f"│  Acciones ejecutadas: {self._execution_stats['total_actions']}")
        logger.info(f"│  Llamadas a IA: {self._execution_stats['total_ai_calls']}")
        logger.info(f"│  Historial de acciones: {len(self.action_history)}")
        logger.info("└" + "─" * 50 + "┘")
        
        # Stats de componentes
        if hasattr(self.ai_orchestrator, 'get_stats'):
            ai_stats = self.ai_orchestrator.get_stats()
            logger.debug(f"TEST_RUNNER: AI Orchestrator stats: {ai_stats}")
        
        if hasattr(self.agent_tools, 'get_action_stats'):
            action_stats = self.agent_tools.get_action_stats()
            logger.debug(f"TEST_RUNNER: Agent Tools stats: {action_stats}")
        
        # DEBUG: Dump del mapeo de elementos (solo en nivel DEBUG)
        logger.debug("TEST_RUNNER: UIParser element map dump:")
        self.ui_parser.debug_dump_element_map(log_output=False)  # Solo retorna, no duplica logs

    def _execute_step(self, step: str, step_index: int) -> bool:
        """
        Ejecuta un paso individual con sistema de reintentos y loop agéntico.

        El loop agéntico permite que después de cada acción se actualice el estado
        de la UI y la IA pueda tomar nuevas decisiones basadas en elementos que
        antes no estaban disponibles (ej: botones deshabilitados que se habilitan
        después de llenar campos).

        Args:
            step: Descripción del paso en lenguaje natural
            step_index: Índice del paso (para logging)

        Returns:
            True si el paso se completó exitosamente, False en caso contrario
        """
        max_actions_per_step = 10  # Límite de acciones por paso para evitar loops infinitos
        actions_executed = 0
        
        logger.debug(f"TEST_RUNNER: Configuración del paso:")
        logger.debug(f"  - Max acciones por paso: {max_actions_per_step}")
        logger.debug(f"  - Max reintentos: {self.max_retries}")

        for attempt in range(1, self.max_retries + 1):
            logger.info("")
            logger.info(f"┌─ INTENTO {attempt}/{self.max_retries} para paso {step_index} ─┐")
            attempt_start = datetime.now()

            try:
                # Loop agéntico: continúa hasta que la IA indique que el paso está completo
                loop_iteration = 0
                while actions_executed < max_actions_per_step:
                    loop_iteration += 1
                    logger.info("")
                    logger.info(f"  ┌─ Loop agéntico iteración {loop_iteration} ─┐")
                    
                    # ══════════════════════════════════════════════════════════════
                    # FASE 1: Obtener XML ACTUALIZADO del driver
                    # ══════════════════════════════════════════════════════════════
                    logger.debug("  │ FASE 1: Obteniendo XML de la pantalla...")
                    phase1_start = time.time()
                    try:
                        xml_source = self.agent_tools.get_screen_tree()
                        phase1_time = int((time.time() - phase1_start) * 1000)
                        logger.debug(f"  │ FASE 1: ✓ XML obtenido en {phase1_time}ms ({len(xml_source)} chars)")
                    except Exception as e:
                        logger.error(f"  │ FASE 1 ERROR: No se pudo obtener XML: {e}")
                        logger.error(f"  │ Traceback:\n{traceback.format_exc()}")
                        raise

                    # ══════════════════════════════════════════════════════════════
                    # FASE 2: UIParser parsea XML y genera JSON con estado ACTUAL
                    # ══════════════════════════════════════════════════════════════
                    logger.debug("  │ FASE 2: Parseando UI...")
                    phase2_start = time.time()
                    try:
                        ui_elements = self.ui_parser.parse_screen(xml_source)
                        phase2_time = int((time.time() - phase2_start) * 1000)
                        logger.info(f"  │ FASE 2: ✓ {len(ui_elements)} elementos encontrados en {phase2_time}ms")
                        
                        # Mostrar elementos encontrados
                        if ui_elements:
                            logger.debug("  │ FASE 2: Elementos disponibles:")
                            for elem in ui_elements[:10]:  # Limitar a 10 para no saturar
                                logger.debug(f"  │   ID {elem['id']}: [{elem['role']}] '{elem['label'][:40]}...' " 
                                           f"{'✓checked' if elem.get('checked') else ''}")
                            if len(ui_elements) > 10:
                                logger.debug(f"  │   ... y {len(ui_elements) - 10} más")
                            # DEBUG: Dump del mapeo completo (solo primera iteración del loop)
                            if loop_iteration == 1:
                                logger.debug("  │ FASE 2: Dump del mapeo ID→XPath:")
                                self.ui_parser.debug_dump_element_map(log_output=False)
                        else:
                            logger.warning("  │ FASE 2 WARNING: No se encontraron elementos interactuables")
                            # DEBUG: Dump para diagnosticar por qué no hay elementos
                            self.ui_parser.debug_dump_element_map(log_output=True)
                    except Exception as e:
                        logger.error(f"  │ FASE 2 ERROR: Fallo al parsear UI: {e}")
                        logger.error(f"  │ Traceback:\n{traceback.format_exc()}")
                        raise

                    # ══════════════════════════════════════════════════════════════
                    # FASE 3: AI Orchestrator decide acción con UI ACTUALIZADA
                    # ══════════════════════════════════════════════════════════════
                    logger.debug("  │ FASE 3: Consultando IA para decidir acción...")
                    phase3_start = time.time()
                    self._execution_stats["total_ai_calls"] += 1
                    try:
                        ai_decision = self.ai_orchestrator.decide_next_action(
                            ui_elements=ui_elements,
                            current_step=step,
                            action_history=self.action_history[-5:],  # Últimas 5 acciones
                            objective=self.objective,
                        )
                        phase3_time = int((time.time() - phase3_start) * 1000)
                        logger.info(f"  │ FASE 3: ✓ Decisión de IA recibida en {phase3_time}ms")
                        
                        # Log de la decisión
                        if ai_decision.get("tool_calls"):
                            for tc in ai_decision["tool_calls"]:
                                logger.info(f"  │ FASE 3: Decisión -> {tc['name']}({tc['arguments']})")
                        else:
                            logger.info(f"  │ FASE 3: Decisión -> Sin tool call (paso completado)")
                            if ai_decision.get("message"):
                                logger.debug(f"  │ FASE 3: Mensaje IA: {ai_decision['message']}")
                    except Exception as e:
                        logger.error(f"  │ FASE 3 ERROR: Fallo en llamada a IA: {e}")
                        logger.error(f"  │ Traceback:\n{traceback.format_exc()}")
                        raise

                    # ══════════════════════════════════════════════════════════════
                    # FASE 4: Ejecutar acción o finalizar paso
                    # ══════════════════════════════════════════════════════════════
                    if ai_decision.get("tool_calls"):
                        logger.debug("  │ FASE 4: Ejecutando acción...")
                        # Ejecutar UNA acción a la vez para mantener UI actualizada
                        tool_call = ai_decision["tool_calls"][0]
                        
                        phase4_start = time.time()
                        success = self._execute_single_tool_call(tool_call, step)
                        phase4_time = int((time.time() - phase4_start) * 1000)
                        self._execution_stats["total_actions"] += 1
                        actions_executed += 1
                        
                        logger.info(f"  │ FASE 4: Acción ejecutada en {phase4_time}ms - "
                                   f"{'✓ Éxito' if success else '✗ Fallo'}")

                        if not success:
                            logger.warning(f"  │ ⚠️ Acción falló, saliendo del loop para reintentar...")
                            logger.info(f"  └─ Fin loop iteración {loop_iteration} (acción fallida) ─┘")
                            break  # Salir del while para reintentar

                        # Registrar acción en historial
                        action_summary = f"Acción: {tool_call['name']}({tool_call['arguments']})"
                        self.action_history.append(action_summary)
                        logger.debug(f"  │ Acción agregada al historial. Total: {len(self.action_history)}")

                        # Esperar a que la UI se actualice
                        logger.debug("  │ Esperando 1s para que la UI se actualice...")
                        time.sleep(1)

                        logger.info(f"  └─ Fin loop iteración {loop_iteration} (continuando) ─┘")
                        # Continuar loop para obtener nuevo estado de UI
                        continue
                    else:
                        # La IA indica que no se requiere más acciones - paso completado
                        logger.info(f"  │ FASE 4: IA indica paso completado")
                        logger.info(f"  │ Mensaje: {ai_decision.get('message', 'Sin mensaje')}")
                        action_summary = f"Paso completado: {step}"
                        self.action_history.append(action_summary)
                        
                        attempt_elapsed = (datetime.now() - attempt_start).total_seconds()
                        logger.info(f"  └─ Fin loop (paso completado en {attempt_elapsed:.2f}s) ─┘")
                        logger.info(f"└─ FIN INTENTO {attempt} - ÉXITO ─┘")
                        return True

                # Si llegamos aquí, se alcanzó el límite de acciones
                if actions_executed >= max_actions_per_step:
                    logger.warning(f"TEST_RUNNER WARNING: Se alcanzó el límite de {max_actions_per_step} acciones por paso")
                    logger.warning(f"TEST_RUNNER: Esto puede indicar un loop infinito o paso mal definido")
                    return False

                # Acción falló, reintentar
                logger.warning(f"⚠️ Intento {attempt} falló, esperando 2s antes de reintentar...")
                time.sleep(2)

            except Exception as e:
                logger.error(f"TEST_RUNNER ERROR: Excepción en intento {attempt}: {type(e).__name__}: {str(e)}")
                logger.error(f"TEST_RUNNER ERROR: Traceback completo:\n{traceback.format_exc()}")
                
                if attempt < self.max_retries:
                    logger.info(f"TEST_RUNNER: Esperando 2s antes de reintentar...")
                    time.sleep(2)
                    continue
                else:
                    logger.error(f"TEST_RUNNER: Se agotaron los {self.max_retries} reintentos")
                    return False

        logger.error(f"TEST_RUNNER: Se agotaron todos los reintentos para el paso {step_index}")
        return False

    def _execute_single_tool_call(self, tool_call: dict, step: str) -> bool:
        """
        Ejecuta una única llamada a herramienta decidida por la IA.

        Esta función ejecuta UNA sola acción para permitir que el loop agéntico
        actualice el estado de la UI después de cada interacción. Esto es crucial
        para manejar elementos dinámicos como botones que se habilitan después
        de llenar campos de formulario.

        Args:
            tool_call: Diccionario con la tool call de la IA
            step: Paso actual (para contexto)

        Returns:
            True si la acción se ejecutó exitosamente
        """
        tool_name = tool_call.get("name", "UNKNOWN")
        tool_args = tool_call.get("arguments", {})
        tool_id = tool_call.get("id", "N/A")

        logger.info("")
        logger.info(f"  ┌─ EJECUTANDO TOOL CALL ─────────────────────────┐")
        logger.info(f"  │ Tool: {tool_name}")
        logger.info(f"  │ Args: {tool_args}")
        logger.info(f"  │ ID: {tool_id}")
        logger.info(f"  │ Paso: {step[:50]}...")
        logger.info(f"  └─────────────────────────────────────────────────┘")

        start_time = time.time()
        
        try:
            result = None

            if tool_name == "touch_element_by_id":
                element_id = tool_args.get("element_id")
                if element_id is None:
                    logger.error(f"TEST_RUNNER ERROR: 'element_id' no presente en arguments: {tool_args}")
                    return False
                logger.debug(f"TEST_RUNNER: Llamando touch_element_by_id(element_id={element_id})")
                result = self.agent_tools.touch_element_by_id(element_id)

            elif tool_name == "fill_field_by_id":
                element_id = tool_args.get("element_id")
                value = tool_args.get("value")
                if element_id is None:
                    logger.error(f"TEST_RUNNER ERROR: 'element_id' no presente en arguments: {tool_args}")
                    return False
                if value is None:
                    logger.error(f"TEST_RUNNER ERROR: 'value' no presente en arguments: {tool_args}")
                    return False
                logger.debug(f"TEST_RUNNER: Llamando fill_field_by_id(element_id={element_id}, value='{value}')")
                result = self.agent_tools.fill_field_by_id(element_id, value)

            elif tool_name == "scroll":
                direction = tool_args.get("direction", "down")
                logger.debug(f"TEST_RUNNER: Llamando scroll(direction='{direction}')")
                result = self.agent_tools.scroll(direction)

            elif tool_name == "go_back":
                logger.debug("TEST_RUNNER: Llamando go_back()")
                result = self.agent_tools.go_back()

            elif tool_name == "assert_screen_contains":
                text = tool_args.get("text")
                if text is None:
                    logger.error(f"TEST_RUNNER ERROR: 'text' no presente en arguments: {tool_args}")
                    return False
                logger.debug(f"TEST_RUNNER: Llamando assert_screen_contains(text='{text}')")
                is_present, message = self.agent_tools.assert_screen_contains(text)
                result = message
                if not is_present:
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    logger.error(f"  ❌ Aserción falló: {message} ({elapsed_ms}ms)")
                    return False

            else:
                logger.error(f"TEST_RUNNER ERROR: Herramienta desconocida: '{tool_name}'")
                logger.error(f"TEST_RUNNER ERROR: Herramientas válidas: touch_element_by_id, fill_field_by_id, scroll, go_back, assert_screen_contains")
                return False

            elapsed_ms = int((time.time() - start_time) * 1000)
            
            # Verificar resultado
            if result and "Error" in result:
                logger.error(f"  ❌ Tool call falló ({elapsed_ms}ms): {result}")
                return False
            elif result:
                logger.info(f"  ✅ Tool call exitosa ({elapsed_ms}ms): {result}")

            return True

        except KeyError as ke:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.error(f"TEST_RUNNER ERROR: Argumento faltante en tool call: {ke}")
            logger.error(f"TEST_RUNNER ERROR: Tool: {tool_name}, Args recibidos: {tool_args}")
            return False
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.error(f"TEST_RUNNER ERROR: Excepción ejecutando {tool_name} ({elapsed_ms}ms)")
            logger.error(f"TEST_RUNNER ERROR: {type(e).__name__}: {str(e)}")
            logger.error(f"TEST_RUNNER ERROR: Traceback:\n{traceback.format_exc()}")
            return False

    def clear_history(self):
        """Limpia el historial de acciones."""
        previous_count = len(self.action_history)
        self.action_history = []
        logger.debug(f"TEST_RUNNER: Historial limpiado ({previous_count} acciones eliminadas)")
    
    def get_execution_stats(self) -> dict:
        """
        DEBUG: Retorna estadísticas de la ejecución actual.
        """
        stats = self._execution_stats.copy()
        stats["action_history_count"] = len(self.action_history)
        stats["elapsed_time"] = (datetime.now() - self._start_time).total_seconds()
        
        # Agregar stats de componentes
        if hasattr(self.ai_orchestrator, 'get_stats'):
            stats["ai_orchestrator"] = self.ai_orchestrator.get_stats()
        if hasattr(self.agent_tools, 'get_action_stats'):
            stats["agent_tools"] = self.agent_tools.get_action_stats()
        
        return stats
    
    def debug_dump_state(self) -> None:
        """
        DEBUG: Imprime el estado actual del test runner para diagnóstico.
        """
        logger.info("")
        logger.info("╔" + "═" * 60 + "╗")
        logger.info("║  DEBUG: ESTADO ACTUAL DEL TEST RUNNER")
        logger.info("╠" + "═" * 60 + "╣")
        logger.info(f"║  Objetivo: {self.objective or 'No definido'}")
        logger.info(f"║  Max reintentos: {self.max_retries}")
        logger.info(f"║  Historial de acciones: {len(self.action_history)} entradas")
        logger.info("║")
        logger.info("║  Estadísticas de ejecución:")
        for key, value in self._execution_stats.items():
            logger.info(f"║    {key}: {value}")
        logger.info("║")
        logger.info("║  Últimas 5 acciones:")
        for action in self.action_history[-5:]:
            logger.info(f"║    - {action[:55]}...")
        logger.info("║")
        logger.info("║  Estado del UIParser:")
        logger.info(f"║    Elementos mapeados: {len(self.ui_parser.element_map)}")
        logger.info(f"║    Próximo ID: {self.ui_parser.current_id}")
        logger.info("╚" + "═" * 60 + "╝")

