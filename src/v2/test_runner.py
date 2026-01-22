"""
Test Runner - Orquesta la ejecución de pruebas usando el agente de IA.

NOTA: Este módulo contiene una optimización para reducir llamadas al orquestador
que está marcada como "ÁREA DE MEJORA POTENCIAL". Ver método:
- _check_if_action_completes_step() (línea ~564)
- Búsqueda: "[OPTIMIZACIÓN - ÁREA DE MEJORA POTENCIAL]"
- Tag: "# TODO/FIXME: Optimización completitud de paso"
"""

import time
import json
import logging
import traceback
from typing import List, Optional, Dict, Any
from datetime import datetime
from appium.webdriver import Remote

from src.ui_parser import UIParser
from src.agent_tools import AppiumSkills
from src.v2.ai_orchestrator import QAIV2Orchestrator, StepContext
from src.config import Config
from src.middleware_result import MiddlewareResult
from src.validators import validate_config, validate_driver, is_recoverable_error

# Importar Allure de forma opcional (solo disponible en tests)
try:
    import allure
    ALLURE_AVAILABLE = True
except ImportError:
    ALLURE_AVAILABLE = False

# Configurar logging con formato detallado
logging.basicConfig(
    level=logging.DEBUG,  # Cambiado a DEBUG para máxima visibilidad
    format='%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class QAIV2TestRunner:
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
        logger.info("  RUNNER: Inicializando QAIV2TestRunner (V2)")
        
        self._start_time = datetime.now()
        
        # Debug: Imprimir configuración actual
        #logger.info("TEST_RUNNER: Imprimiendo configuración...")
        #Config.debug_print_config()
        
        # Validar configuración
        validate_config()
        
        self.driver = driver
        self.objective = objective
        
        # Verificar driver
        validate_driver(driver)
        
        # Inicializar componentes
        self.ui_parser = UIParser(driver=self.driver)
        self.agent_tools = AppiumSkills(driver, self.ui_parser)
        self.ai_orchestrator = QAIV2Orchestrator()
        
        # Contexto global del agente para el paso actual
        self.current_context: Optional[StepContext] = None
        # V2: action_history incluye resultados (formato dict)
        self.action_history: List[Dict[str, Any]] = []
        self.max_retries = Config.MAX_RETRIES_PER_STEP
        
        # Estadísticas de ejecución
        self._execution_stats = {
            "total_steps": 0,
            "completed_steps": 0,
            "failed_steps": 0,
            "total_actions": 0,
            "total_ai_calls": 0,
            "start_time": self._start_time.isoformat(),
        }
        
        logger.info(f"  RUNNER: ✓ Inicialización completa")

    def run_test_plan(self, test_plan: List[str]) -> bool:
        """
        Ejecuta un plan de prueba con pasos en lenguaje natural.

        Args:
            test_plan: Lista de pasos a ejecutar en lenguaje natural

        Returns:
            True si todos los pasos se completaron exitosamente, False en caso contrario
        """
        logger.info("█" * 80)
        logger.info("█  RUNNER: INICIANDO EJECUCIÓN DE PLAN")
        logger.info("█" * 80)
        
        plan_start_time = datetime.now()
        self._execution_stats["total_steps"] = len(test_plan)
        
        logger.info(f"  Plan: {len(test_plan)} pasos | Max reintentos: {self.max_retries}")
        if self.objective:
            logger.info(f"  Objetivo: '{self.objective}'")
        
        # Listar todos los pasos
        logger.info("TEST_RUNNER: Plan de prueba:")
        for idx, step in enumerate(test_plan, 1):
            logger.info(f"  {idx}. {step}")
        logger.info("")

        step_index = 0
        while step_index < len(test_plan):
            step = test_plan[step_index]
            display_index = step_index + 1
            step_start_time = datetime.now()
            
            logger.info("")
            logger.info("═" * 80)
            logger.info(f"▶ PASO {display_index}/{len(test_plan)}: {step}")
            logger.info("═" * 80)
            logger.info(f"TEST_RUNNER: Iniciando paso {display_index} a las {step_start_time.strftime('%H:%M:%S.%f')[:-3]}")

            # Calcular previous_step / next_step para el contexto del plan
            previous_step = test_plan[step_index - 1] if step_index > 0 else None
            next_step = test_plan[step_index + 1] if step_index < len(test_plan) - 1 else None

            # Ejecutar el paso
            result = self._execute_step(
                step=step,
                step_index=display_index,
                total_steps=len(test_plan),
                previous_step=previous_step,
                next_step=next_step,
            )
            
            step_elapsed = (datetime.now() - step_start_time).total_seconds()

            if not result.get("success"):
                self._execution_stats["failed_steps"] += 1
                logger.error("")
                logger.error("╔" + "═" * 78 + "╗")
                logger.error(f"║ ❌ FALLO EN PASO {display_index}: {step[:60]}")
                logger.error("╚" + "═" * 78 + "╝")
                logger.error(f"  RUNNER: Tiempo en paso fallido: {step_elapsed:.2f}s")
                
                # Resumen de estadísticas
                self._print_execution_summary(plan_start_time)
                return False

            # Determinar cuántos pasos avanzar (cascada)
            steps_to_advance = result.get("steps_advanced", 1)
            self._execution_stats["completed_steps"] += steps_to_advance
            
            if steps_to_advance > 1:
                logger.info("")
                logger.info(f"🚀 CASCADA: Se han completado {steps_to_advance} pasos de golpe")
                for i in range(steps_to_advance):
                    completed_step_desc = test_plan[step_index + i]
                    logger.info(f"✅ PASO {step_index + i + 1} COMPLETADO: {completed_step_desc}")
            else:
                logger.info("")
                logger.info(f"✅ PASO {display_index} COMPLETADO en {step_elapsed:.2f}s")
            
            logger.info("")
            
            # Avanzar el índice
            step_index += steps_to_advance

        # Plan completado exitosamente
        plan_elapsed = (datetime.now() - plan_start_time).total_seconds()
        
        logger.info("")
        logger.info("█" * 80)
        logger.info("█  ✅ PLAN DE PRUEBA COMPLETADO")
        logger.info("█" * 80)
        logger.info(f"  RUNNER: Tiempo total: {plan_elapsed:.2f}s")
        
        # Capturar screenshot final automáticamente para Allure
        self._capture_final_screenshot()
        
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
            logger.debug(f"  RUNNER: AI Orchestrator stats: {ai_stats}")
        
        if hasattr(self.agent_tools, 'get_action_stats'):
            action_stats = self.agent_tools.get_action_stats()
            logger.debug(f"  RUNNER: Agent Tools stats: {action_stats}")
        
        # Dump del mapeo de elementos (solo en nivel DEBUG)
        logger.debug("  RUNNER: Dumping element map...")
        self.ui_parser.debug_dump_element_map(log_output=False)

    def _capture_final_screenshot(self) -> None:
        """
        Captura un screenshot final automáticamente y lo adjunta a Allure.
        Se ejecuta después de completar exitosamente todos los pasos del plan.
        """
        if not ALLURE_AVAILABLE:
            logger.debug("  RUNNER: Allure no disponible, omitiendo screenshot final")
            return
        
        try:
            logger.info("  RUNNER: Capturando screenshot final para Allure...")
            screenshot = self.driver.get_screenshot_as_png()
            allure.attach(
                screenshot,
                name="Final - Estado después de completar todos los pasos",
                attachment_type=allure.attachment_type.PNG
            )
            logger.info("  RUNNER: ✓ Screenshot final adjuntado a Allure")
        except Exception as e:
            logger.warning(f"  RUNNER: No se pudo capturar screenshot final: {e}")

    def _execute_step(
        self,
        step: str,
        step_index: int,
        total_steps: int,
        previous_step: Optional[str],
        next_step: Optional[str],
    ) -> Dict[str, Any]:
        """
        Ejecuta un paso individual con sistema de reintentos y loop agéntico.

        El loop agéntico permite que después de cada acción se actualice el estado
        de la UI y la IA pueda tomar nuevas decisiones basadas en elementos que
        antes no estaban disponibles (ej: botones deshabilitados que se habilitan
        después de llenar campos).

        Args:
            step: Descripción del paso en lenguaje natural
            step_index: Índice del paso (para logging, 1-based)
            total_steps: Número total de pasos del plan
            previous_step: Paso anterior (o None si es el primero)
            next_step: Próximo paso (o None si es el último)

        Returns:
            Dict con {"success": bool, "steps_advanced": int}
        """
        # Límites de acciones (desde Config para permitir personalización via .env)
        max_actions_per_step = Config.MAX_ACTIONS_PER_STEP
        max_repeated_action_attempts = Config.MAX_REPEATED_ACTION_ATTEMPTS
        actions_executed = 0
        
        # Tracking de acciones repetidas (inicializar ANTES del loop de reintentos)
        last_tool_call = {}
        last_result_message = ""
        last_action_signature = None
        repeated_action_count = 0
        
        for attempt in range(1, self.max_retries + 1):
            logger.info("")
            logger.info(f"┌─ INTENTO {attempt}/{self.max_retries} para paso {step_index} ─┐")
            attempt_start = datetime.now()

            try:
                # Loop agéntico: continúa hasta que la IA indique que el paso está completo
                loop_iteration = 0
                current_ui_elements = None
                while actions_executed < max_actions_per_step:
                    loop_iteration += 1
                    logger.info("")
                    logger.info(f"  ┌─ Loop agéntico iteración {loop_iteration} ─┐")
                    
                    # Resetear conteo de acciones repetidas en cada nueva iteración del loop agéntico
                    # Esto permite que si la UI cambió, la IA pueda reintentar acciones similares
                    repeated_action_count = 0
                    last_action_signature = None
                    
                    # ══════════════════════════════════════════════════════════════
                    # FASE: Obtener UI actual (UIParser maneja todo internamente)
                    # ══════════════════════════════════════════════════════════════
                    # UIParser.get_ui() encapsula:
                    # - Espera de estabilidad de UI
                    # - Obtención de XML y current_package
                    # - Validación de middleware (scope de apps)
                    # - Parseo de elementos
                    # Retorna List[UIElement] o MiddlewareResult
                    phase_start = time.time()
                    try:
                        # OPTIMIZACIÓN: Solo obtener UI si no la tenemos ya (cacheada del paso anterior o feedback de tool)
                        if current_ui_elements is None:
                            logger.info("  │ FASE 2: Obteniendo UI de la pantalla...")
                            parse_result = self.ui_parser.get_ui()
                        else:
                            logger.info(f"  │ FASE 2: Usando UI cacheada ({len(current_ui_elements)} elementos)")
                            parse_result = current_ui_elements
                            
                        phase_time = int((time.time() - phase_start) * 1000)
                        
                        # El middleware retorna MiddlewareResult o List[UIElement]
                        if isinstance(parse_result, MiddlewareResult):
                            # Middleware denegó: app no permitida
                            ui_elements = []
                            current_ui_elements = None # Forzar re-parse si hay denegación (?)
                            logger.warning(f"  │ ⚠️  Middleware denegado ({phase_time}ms)")
                            # ... resto del código igual ...
                            logger.warning(f"  │ {parse_result.message}")
                            # Inyectar mensaje en action_history para que el agente lo vea
                            self.action_history.append({
                                "index": len(self.action_history) + 1,
                                "action": "get_ui_elements",
                                "result": parse_result.message,
                                "success": False,
                                "middleware_denied": True,
                                "allowed_apps": parse_result.allowed_apps,
                                "suggested_tool": parse_result.suggested_tool
                            })
                        else:
                            # Resultado normal: lista de elementos
                            ui_elements = parse_result
                            logger.info(f"  │ ✓ {len(ui_elements)} elementos encontrados en {phase_time}ms")
                            
                            # Mostrar elementos encontrados
                            if ui_elements:
                                #logger.debug("  │ FASE 2: Elementos disponibles:")
                                #logger.debug(f"  │ {json.dumps(ui_elements, indent=2, ensure_ascii=False)}")
                                # DEBUG: Dump del mapeo completo (solo primera iteración del loop)
                                if loop_iteration == 1:
                                    #logger.debug("  │ FASE 2: Dump del mapeo ID→XPath:")
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
                    logger.info("  │ FASE 3: Consultando IA para decidir acción...")
                    phase3_start = time.time()
                    self._execution_stats["total_ai_calls"] += 1
                    try:
                        # Construir StepContext rico para este ciclo del loop agéntico
                        try:
                            app_states = {}
                            get_states = getattr(self.agent_tools, "get_tracked_app_states", None)
                            if callable(get_states):
                                app_states = get_states() or {}
                        except Exception as e:
                            logger.warning(
                                "TEST_RUNNER: No se pudo obtener estados de apps desde AppiumSkills: %s",
                                e,
                            )
                            app_states = {}

                        # V2: action_history ya está en formato dict con action, result, success
                        recent_actions = self.action_history[-5:] if self.action_history else []

                        step_context = StepContext(
                            objective=self.objective,
                            step_index=step_index,
                            total_steps=total_steps,
                            current_step=step,
                            next_step=next_step,
                            previous_step=previous_step,
                            action_history=recent_actions,
                            ui_elements=parse_result if isinstance(parse_result, list) else [],
                            app_states=app_states,
                        )
                        self.current_context = step_context

                        ai_decision = self.ai_orchestrator.decide_next_action(
                            ui_elements=parse_result if isinstance(parse_result, list) else [],
                            context=step_context,
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
                        logger.debug(f"  │ FASE 4: Ejecutando {len(ai_decision['tool_calls'])} acción(es)...")
                        
                        # ══════════════════════════════════════════════════════════════
                        # V2: Ejecutar MÚLTIPLES tool calls en el mismo paso
                        # El agente puede ejecutar varias acciones si todas pertenecen al paso actual
                        # ══════════════════════════════════════════════════════════════
                        all_actions_successful = True
                        last_tool_call = None
                        last_result_message = None
                        
                        for tool_call_idx, tool_call in enumerate(ai_decision["tool_calls"]):
                            logger.info(f"  │ Ejecutando acción {tool_call_idx + 1}/{len(ai_decision['tool_calls'])}: {tool_call['name']}")
                            
                            # ══════════════════════════════════════════════════════════════
                            # DETECCIÓN DE ACCIONES REPETIDAS
                            # Si la IA intenta la misma acción 3 veces, falla el paso
                            # ══════════════════════════════════════════════════════════════
                            current_action_signature = f"{tool_call['name']}:{json.dumps(tool_call['arguments'], sort_keys=True)}"
                            
                            if current_action_signature == last_action_signature:
                                repeated_action_count += 1
                                logger.warning(f"  │ ⚠️ ACCIÓN REPETIDA detectada ({repeated_action_count}/{max_repeated_action_attempts})")
                                logger.warning(f"  │    Acción: {tool_call['name']}({tool_call['arguments']})")
                                
                                if repeated_action_count >= max_repeated_action_attempts:
                                    logger.error("")
                                    logger.error("  ╔" + "═" * 70 + "╗")
                                    logger.error("  ║ ❌ ERROR: LÍMITE DE ACCIONES REPETIDAS ALCANZADO")
                                    logger.error("  ╠" + "═" * 70 + "╣")
                                    logger.error(f"  ║ La IA intentó la misma acción {max_repeated_action_attempts} veces sin progreso")
                                    logger.error(f"  ║ Acción: {tool_call['name']}")
                                    logger.error(f"  ║ Args: {tool_call['arguments']}")
                                    logger.error("  ║")
                                    logger.error("  ║ Esto indica que la acción se ejecuta pero no produce")
                                    logger.error("  ║ el efecto esperado (ej: campo no acepta texto).")
                                    logger.error("  ║")
                                    logger.error("  ║ Posibles causas:")
                                    logger.error("  ║   - El elemento está visible pero no interactuable")
                                    logger.error("  ║   - El campo tiene validación que rechaza el input")
                                    logger.error("  ║   - Hay un overlay/popup bloqueando la interacción")
                                    logger.error("  ║   - El elemento correcto tiene diferente XPath")
                                    logger.error("  ╚" + "═" * 70 + "╝")
                                    return False
                            else:
                                # Nueva acción diferente, resetear contador y actualizar firma
                                repeated_action_count = 1
                                last_action_signature = current_action_signature
                            
                            phase4_start = time.time()
                            success, result_message = self._execute_single_tool_call(tool_call, step)
                            phase4_time = int((time.time() - phase4_start) * 1000)
                            self._execution_stats["total_actions"] += 1
                            actions_executed += 1
                            
                            logger.info(f"  │   Acción {tool_call_idx + 1} ejecutada en {phase4_time}ms - "
                                       f"{'✓ Éxito' if success else '✗ Fallo'}")

                            if not success:
                                all_actions_successful = False
                                logger.warning(f"  │ ⚠️ Acción {tool_call_idx + 1} falló")
                                # Continuar ejecutando las demás acciones, pero marcar que hubo fallo
                            
                            # V2: Extraer UI del resultado si está disponible
                            result_ui_elements = None
                            result_message_clean = result_message
                            if isinstance(result_message, dict):
                                result_ui_elements = result_message.get("ui_elements")
                                result_message_clean = result_message.get("message", str(result_message))
                                # Si hay UI en el resultado, actualizar current_ui_elements para el siguiente ciclo
                                if result_ui_elements:
                                    current_ui_elements = result_ui_elements
                                    logger.debug(f"  │   ✓ UI actualizada desde resultado ({len(current_ui_elements)} elementos)")
                                else:
                                    # Si la acción fue exitosa pero no nos dio UI, invalidamos cache
                                    # para forzar get_ui() en la siguiente iteración si es necesario
                                    if success:
                                        logger.debug("  │   ⚠ Resultado sin UI, invalidando cache para próxima iteración")
                                        current_ui_elements = None
                            
                            # V2: Registrar acción con resultado en historial (formato dict)
                            # NOTA: NO incluimos UI en el historial para evitar llenar el contexto
                            action_entry = {
                                "index": len(self.action_history) + 1,
                                "action": f"{tool_call['name']}({tool_call['arguments']})",
                                "result": result_message_clean,
                                "success": success
                            }
                            self.action_history.append(action_entry)
                            
                            # Guardar última acción y resultado para consulta de completitud
                            last_tool_call = tool_call
                            last_result_message = result_message_clean
                            
                            # ══════════════════════════════════════════════════════════════
                            # FASE 5: Esperar a que la UI se estabilice después de cada acción
                            # (excepto para assert_screen_contains que no modifica UI)
                            # ══════════════════════════════════════════════════════════════
                            action_name = tool_call['name']
                            if action_name != "assert_screen_contains":
                                logger.debug(f"  │   Esperando estabilidad de UI post-acción {tool_call_idx + 1}...")
                                phase5_start = time.time()
                                is_stable, wait_time, stability_reason = self.agent_tools.wait_for_ui_stable()
                                phase5_time = int((time.time() - phase5_start) * 1000)
                                
                                if is_stable:
                                    logger.debug(f"  │   ✓ UI estable en {phase5_time}ms ({stability_reason})")
                                else:
                                    logger.warning(f"  │   ⚠️ UI no estabilizó en {phase5_time}ms ({stability_reason})")
                        
                        # Después de ejecutar todas las acciones, verificar si alguna falló
                        if not all_actions_successful:
                            logger.warning(f"  │ ⚠️ Al menos una acción falló, saliendo del loop para reintentar...")
                            logger.info(f"  └─ Fin loop iteración {loop_iteration} (acción fallida) ─┘")
                            break  # Salir del while para reintentar
                        
                        logger.debug(f"  │ ✓ Todas las acciones ejecutadas. Total en historial: {len(self.action_history)}")
                        
                        # V2: INMEDIATAMENTE consultar LLM con el resultado para determinar completitud
                        # Solo consultamos una vez después de ejecutar todas las acciones del turno
                        logger.info("  │ FASE 4.5: Consultando IA para determinar completitud del paso...")
                        phase4_5_start = time.time()
                        try:
                            completion_decision = self.ai_orchestrator.decide_step_completion(
                                context=step_context,
                                last_action=last_tool_call,
                                last_result=last_result_message,
                                current_ui=current_ui_elements or (parse_result if isinstance(parse_result, list) else [])
                            )
                            phase4_5_time = int((time.time() - phase4_5_start) * 1000)
                            logger.info(f"  │ FASE 4.5: ✓ Decisión de completitud recibida en {phase4_5_time}ms")
                            
                            if completion_decision.get("step_completed"):
                                logger.info(f"  │ ✓ IA indica que el paso está completo")
                                logger.info(f"  │   Razón: {completion_decision.get('reason', 'N/A')}")
                                
                                # GUARD CLAUSE: Registrar éxito del paso actual
                                action_summary = {
                                    "index": len(self.action_history) + 1,
                                    "action": f"Paso completado: {step}",
                                    "result": completion_decision.get('reason', 'Step completed'),
                                    "success": True
                                }
                                self.action_history.append(action_summary)
                                
                                # CASCADE CHECK: Verificamos el siguiente paso (N+1)
                                steps_advanced = 1
                                # next_step se pasó como argumento a _execute_step
                                if next_step:
                                    logger.info(f"  │ 🔍 CASCADE CHECK: ¿El siguiente paso ya está listo? ('{next_step[:40]}...')")
                                    try:
                                        # Reutilizamos la misma UI para el check del siguiente paso
                                        ui_for_cascading = current_ui_elements or (parse_result if isinstance(parse_result, list) else [])
                                        
                                        next_decision = self.ai_orchestrator.decide_step_completion(
                                            context=step_context,
                                            last_action=last_tool_call,
                                            last_result=last_result_message,
                                            current_ui=ui_for_cascading,
                                            override_step_description=next_step
                                        )
                                        
                                        if next_decision.get("step_completed"):
                                            logger.info(f"  │ 🚀 CASCADE SUCCESS: ¡El paso siguiente TAMBIÉN está completo!")
                                            logger.info(f"  │   Razón: {next_decision.get('reason', 'N/A')}")
                                            steps_advanced = 2
                                            
                                            # Registrar el paso auto-completado
                                            next_action_summary = {
                                                "index": len(self.action_history) + 1,
                                                "action": f"Paso autocompletado (cascada): {next_step}",
                                                "result": next_decision.get('reason', 'Auto-completed via cascading check'),
                                                "success": True
                                            }
                                            self.action_history.append(next_action_summary)
                                    except Exception as e:
                                        logger.warning(f"  │ ⚠️ Error en Cascade Check: {e}")

                                attempt_elapsed = (datetime.now() - attempt_start).total_seconds()
                                logger.info(f"  └─ Fin loop (paso completado en {attempt_elapsed:.2f}s) ─┘")
                                logger.info(f"└─ FIN INTENTO {attempt} - ÉXITO ─┘")
                                
                                return {
                                    "success": True,
                                    "steps_advanced": steps_advanced
                                }
                            else:
                                logger.info(f"  │ IA indica que el paso necesita más acciones")
                                logger.info(f"  │   Razón: {completion_decision.get('reason', 'N/A')}")
                        except Exception as e:
                            logger.warning(f"  │ FASE 4.5 WARNING: Error consultando completitud: {e}")
                            logger.warning(f"  │ Continuando con flujo normal...")
                            # Continuar con flujo normal si falla la consulta de completitud

                        logger.info(f"  └─ Fin loop iteración {loop_iteration} (continuando) ─┘")
                        # Continuar loop para obtener nuevo estado de UI
                        continue
                    else:
                        # La IA indica que no se requiere más acciones - paso completado
                        logger.info(f"  │ FASE 4: IA indica paso completado")
                        logger.info(f"  │ Mensaje: {ai_decision.get('message', 'Sin mensaje')}")
                        action_summary = {
                            "index": len(self.action_history) + 1,
                            "action": f"Paso completado: {step}",
                            "result": ai_decision.get('message', 'Step completed'),
                            "success": True
                        }
                        self.action_history.append(action_summary)

                        # CASCADE CHECK: Verificamos el siguiente paso (N+1)
                        steps_advanced = 1
                        if next_step:
                            logger.info(f"  │ 🔍 CASCADE CHECK: ¿El siguiente paso ya está listo? ('{next_step[:40]}...')")
                            try:
                                # Reutilizamos la misma UI para el check del siguiente paso
                                # current_ui_elements contiene la UI actual parseada
                                ui_for_cascading = current_ui_elements or []
                                
                                next_decision = self.ai_orchestrator.decide_step_completion(
                                    context=step_context,
                                    last_action={}, # No hubo acción en esta iteración
                                    last_result="Paso ya completado según análisis inicial",
                                    current_ui=ui_for_cascading,
                                    override_step_description=next_step
                                )
                                
                                if next_decision.get("step_completed"):
                                    logger.info(f"  │ 🚀 CASCADE SUCCESS: ¡El paso siguiente TAMBIÉN está completo!")
                                    logger.info(f"  │   Razón: {next_decision.get('reason', 'N/A')}")
                                    steps_advanced = 2
                                    
                                    # Registrar el paso auto-completado
                                    next_action_summary = {
                                        "index": len(self.action_history) + 1,
                                        "action": f"Paso autocompletado (cascada): {next_step}",
                                        "result": next_decision.get('reason', 'Auto-completed via cascading check'),
                                        "success": True
                                    }
                                    self.action_history.append(next_action_summary)
                            except Exception as e:
                                logger.warning(f"  │ ⚠️ Error en Cascade Check: {e}")
                        
                        attempt_elapsed = (datetime.now() - attempt_start).total_seconds()
                        logger.info(f"  └─ Fin loop (paso completado en {attempt_elapsed:.2f}s) ─┘")
                        logger.info(f"└─ FIN INTENTO {attempt} - ÉXITO ─┘")
                        return {
                            "success": True,
                            "steps_advanced": steps_advanced
                        }

                # Si llegamos aquí, se alcanzó el límite de acciones
                if actions_executed >= max_actions_per_step:
                    logger.warning(f"TEST_RUNNER WARNING: Se alcanzó el límite de {max_actions_per_step} acciones por paso")
                    logger.warning(f"TEST_RUNNER: Esto puede indicar un loop infinito o paso mal definido")
                    return {"success": False, "steps_advanced": 0}

                # Acción falló, reintentar
                logger.warning(f"⚠️ Intento {attempt} falló, esperando 2s antes de reintentar...")
                time.sleep(2)

            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)
                logger.error(f"TEST_RUNNER ERROR: Excepción en intento {attempt}: {error_type}: {error_msg}")
                logger.error(f"TEST_RUNNER ERROR: Traceback completo:\n{traceback.format_exc()}")
                
                # Verificar si el error es recuperable
                is_recoverable = is_recoverable_error(e)
                
                if not is_recoverable:
                    # Error NO recuperable - no reintentar, fallar inmediatamente
                    logger.error(f"TEST_RUNNER ERROR: Error NO recuperable ({error_type}) - no se reintentará")
                    logger.error(f"TEST_RUNNER ERROR: Este tipo de error no se puede solucionar con reintentos")
                    logger.error(f"TEST_RUNNER ERROR: Revisa la configuración, estructura de datos o código")
                    return {"success": False, "steps_advanced": 0}
                
                # Error recuperable - reintentar si quedan intentos
                if attempt < self.max_retries:
                    logger.warning(f"TEST_RUNNER: Error recuperable ({error_type}) - reintentando...")
                    logger.info(f"TEST_RUNNER: Esperando 2s antes de reintentar...")
                    time.sleep(2)
                    continue
                else:
                    logger.error(f"TEST_RUNNER: Se agotaron los {self.max_retries} reintentos para error recuperable")
                    return {"success": False, "steps_advanced": 0}

        logger.error(f"TEST_RUNNER: Se agotaron todos los reintentos para el paso {step_index}")
        return {"success": False, "steps_advanced": 0}

    def _check_if_action_completes_step(self, action_name: str, action_args: dict, step: str) -> bool:
        """
        [OPTIMIZACIÓN - ÁREA DE MEJORA POTENCIAL]
        
        Verifica si una acción ejecutada exitosamente completa directamente el paso.
        Esto permite evitar una segunda llamada innecesaria al orquestador cuando
        es obvio que el paso está completo.
        
        **PROPÓSITO ACTUAL:**
        Reducir llamadas innecesarias al orquestador para pasos simples de una acción,
        mejorando el rendimiento y reduciendo costos de API.
        
        **LIMITACIONES CONOCIDAS:**
        1. Usa análisis de palabras clave en texto del paso (matching de strings)
           - Puede fallar con variaciones en redacción
           - No comprende semántica real del paso
        2. No considera contexto completo:
           - No verifica si el paso requiere múltiples acciones
           - No valida el resultado de la acción ejecutada
        3. Puede ser demasiado agresivo:
           - Podría marcar pasos como completos cuando no lo están
           - Ejemplo: "Ingresar usuario" ejecuta fill_field, pero el paso también
             requiere "y hacer click en siguiente" (paso multi-acción)
        
        **ALTERNATIVAS FUTURAS A EVALUAR:**
        1. **Delegación completa a IA**: Eliminar esta función y siempre hacer
           segunda consulta. La IA puede indicar si el paso quedó completo.
           
        2. **Modelo ligero dedicado**: Usar un modelo más pequeño/rápido para
           solo esta verificación de completitud.
           
        3. **Análisis semántico mejorado**: Usar embeddings o parsing más
           sofisticado para entender el tipo de paso.
           
        4. **Sistema de reglas configurables**: Definir reglas explícitas por
           tipo de paso (configurable vía YAML/JSON).
           
        5. **Metadatos en pasos**: Permitir que los pasos incluyan metadatos
           que indiquen si son de una acción o múltiples acciones.
           
        6. **Respuesta de IA en tool_call**: Permitir que la IA en la primera
           llamada indique "ejecuta X y esto completa el paso".
        
        **BUSCAR ESTE CÓDIGO:**
        - Nombre del método: "_check_if_action_completes_step"
        - Comentario: "[OPTIMIZACIÓN - ÁREA DE MEJORA POTENCIAL]"
        - Tag de búsqueda: "# TODO/FIXME: Optimización completitud de paso"
        
        Args:
            action_name: Nombre de la acción ejecutada
            action_args: Argumentos de la acción
            step: Texto del paso actual
            
        Returns:
            True si la acción completa el paso, False si necesita verificación adicional
        """
        step_lower = step.lower()
        
        # Pasos de "Esperar/Verificar/Comprobar": assert_screen_contains los completa
        # NOTA: Un assert exitoso SIEMPRE completa el paso porque:
        # 1. Un assert no modifica la UI, por lo que no tiene sentido volver a parsear
        # 2. Si el assert fue exitoso, la verificación pasó
        if action_name == "assert_screen_contains":
            # Lista de keywords incluyendo conjugaciones comunes
            verification_keywords = [
                "esperar", "espera",           # esperar a ver X
                "verificar", "verifica",       # verificar que X / verifica que X
                "comprobar", "comprueba",      # comprobar que X
                "validar", "valida",           # validar que X
                "confirmar", "confirma",       # confirmar que X
                "revisar", "revisa",           # revisar que X
                "ver ", "vea",                 # ver que X aparezca
                "asegurar", "asegura",         # asegurar que X
                "chequear", "chequea",         # chequear que X
            ]
            if any(keyword in step_lower for keyword in verification_keywords):
                logger.debug(f"  │ OPTIMIZACIÓN: assert_screen_contains exitoso en paso de verificación → paso completo")
                return True
            # Incluso si no coincide con keywords, un assert exitoso generalmente completa un paso
            # porque la verificación ya pasó
            logger.debug(f"  │ OPTIMIZACIÓN: assert_screen_contains exitoso → paso completo (assert no modifica UI)")
            return True
        
        # Pasos de "Ingresar/Escribir/Introducir": fill_field_by_id los completa
        if action_name == "fill_field_by_id":
            input_keywords = ["ingresar", "escribir", "introducir", "llenar", "completar campo"]
            if any(keyword in step_lower for keyword in input_keywords):
                # Verificar que el valor ingresado coincida con lo esperado en el paso
                value_entered = action_args.get("value", "").lower()
                if value_entered and value_entered in step_lower:
                    logger.debug(f"  │ OPTIMIZACIÓN: fill_field_by_id exitoso con valor esperado → paso completo")
                    return True
        
        # Pasos de "Tocar/Hacer clic/Click": touch_element_by_id los completa
        if action_name == "touch_element_by_id":
            click_keywords = ["tocar", "hacer clic", "clic", "click", "presionar", "pulsar"]
            if any(keyword in step_lower for keyword in click_keywords):
                logger.debug(f"  │ OPTIMIZACIÓN: touch_element_by_id exitoso en paso de click → paso completo")
                return True
        
        # Por defecto, no asumimos que está completo (dejar que la IA lo verifique)
        return False

    def _execute_single_tool_call(self, tool_call: dict, step: str) -> tuple[bool, str]:
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
            Tupla (success: bool, result: str)
            - success: True si la acción se ejecutó exitosamente
            - result: Mensaje de éxito/error (ej: "Success: Clicked element 5")
        """
        tool_name = tool_call.get("name", "UNKNOWN")
        tool_args = tool_call.get("arguments", {})
        tool_id = tool_call.get("id", "N/A")

        logger.info("")
        logger.info(f"  ┌─ TOOL CALL ─────────────────────────┐")
        logger.info(f"  │ Tool: {tool_name}")
        logger.info(f"  │ Args: {tool_args}")
        logger.info(f"  │ ID: {tool_id}")
        logger.info(f"  │ Status: Inprogress")
        logger.info(f"  │ Step: {step[:50]}...")
        logger.info(f"  └─────────────────────────────────────────────────┘")

        start_time = time.time()
        
        try:
            result = None

            if tool_name == "touch_element_by_id":
                element_id = tool_args.get("element_id")
                if element_id is None:
                    logger.error(f"  RUNNER ERROR: 'element_id' no presente en arguments: {tool_args}")
                    return (False, "Error: element_id missing")
                result = self.agent_tools.touch_element_by_id(element_id)

            elif tool_name == "touch_out_element":
                element_id = tool_args.get("element_id")
                direction = tool_args.get("direction")
                distance_percent = tool_args.get("distance_percent")
                if element_id is None:
                    logger.error(f"  RUNNER ERROR: 'element_id' no presente en arguments: {tool_args}")
                    return (False, "Error: element_id missing")
                if direction is None:
                    logger.error(f"  RUNNER ERROR: 'direction' no presente en arguments: {tool_args}")
                    return (False, "Error: direction missing")
                if distance_percent is None:
                    logger.error(f"  RUNNER ERROR: 'distance_percent' no presente in arguments: {tool_args}")
                    return (False, "Error: distance_percent missing")
                result = self.agent_tools.touch_out_element(element_id, direction, distance_percent)

            elif tool_name == "fill_field_by_id":
                element_id = tool_args.get("element_id")
                value = tool_args.get("value")
                if element_id is None:
                    logger.error(f"  RUNNER ERROR: 'element_id' no presente en arguments: {tool_args}")
                    return (False, "Error: element_id missing")
                if value is None:
                    logger.error(f"  RUNNER ERROR: 'value' no presente en arguments: {tool_args}")
                    return (False, "Error: value missing")
                result = self.agent_tools.fill_field_by_id(element_id, value)

            elif tool_name == "scroll_screen":
                direction = tool_args.get("direction", "down")
                result = self.agent_tools.scroll_screen(direction)

            elif tool_name == "scroll_in_element":
                element_id = tool_args.get("element_id")
                direction = tool_args.get("direction", "down")
                scroll_count = tool_args.get("scroll_count", 1)
                item_multiplier = tool_args.get("item_multiplier", 1)
                if element_id is None:
                    logger.error(f"  RUNNER ERROR: 'element_id' no presente en arguments: {tool_args}")
                    return (False, "Error: element_id missing")
                result = self.agent_tools.scroll_in_element(element_id, direction, scroll_count, item_multiplier)

            elif tool_name == "go_back":
                result = self.agent_tools.go_back()

            elif tool_name == "assert_screen_contains":
                text = tool_args.get("text")
                if text is None:
                    logger.error(f"  RUNNER ERROR: 'text' no presente en arguments: {tool_args}")
                    return (False, "Error: text missing")
                is_present, message = self.agent_tools.assert_screen_contains(text)
                result = message
                if not is_present:
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    logger.error(f"  ❌ Aserción falló: {message} ({elapsed_ms}ms)")
                    return (False, message)

            # ═══════════════════════════════════════════════════════════════
            # HERRAMIENTAS DE GESTIÓN MULTI-APP
            # ═══════════════════════════════════════════════════════════════
            elif tool_name == "activate_app":
                app_package = tool_args.get("app_package")
                if not app_package:
                    logger.error(f"  RUNNER ERROR: 'app_package' no presente en arguments: {tool_args}")
                    return (False, "Error: app_package missing")
                result = self.agent_tools.activate_app(app_package)
                
                # V2: Si activate_app devuelve UI, actualizar ui_elements y resultado
                if isinstance(result, dict) and result.get("ui_available"):
                    ui_elements_from_tool = result.get("ui_elements", [])
                    if ui_elements_from_tool:
                        # Actualizar ui_elements para que esté disponible en el siguiente ciclo
                        ui_elements = ui_elements_from_tool
                        logger.debug(f"  │ ✓ UI actualizada desde activate_app ({len(ui_elements)} elementos)")
                        # El resultado incluirá la UI para que el agente la vea
                        result = result.get("message", "Success: App activated")
                        # Marcar que hay UI disponible en el resultado
                        result_with_ui = {
                            "message": result,
                            "ui_elements": ui_elements_from_tool
                        }
                        result = result_with_ui

            elif tool_name == "terminate_app":
                app_package = tool_args.get("app_package")
                if not app_package:
                    logger.error(f"  RUNNER ERROR: 'app_package' no presente en arguments: {tool_args}")
                    return (False, "Error: app_package missing")
                result = self.agent_tools.terminate_app(app_package)

            elif tool_name == "switch_to_app":
                app_package = tool_args.get("app_package")
                if not app_package:
                    logger.error(f"  RUNNER ERROR: 'app_package' no presente en arguments: {tool_args}")
                    return (False, "Error: app_package missing")
                result = self.agent_tools.switch_to_app(app_package)

            elif tool_name == "switch_to_app_keep_background":
                app_package = tool_args.get("app_package")
                if not app_package:
                    logger.error(f"  RUNNER ERROR: 'app_package' no presente en arguments: {tool_args}")
                    return (False, "Error: app_package missing")
                result = self.agent_tools.switch_to_app_keep_background(app_package)

            # ═══════════════════════════════════════════════════════════════
            # HERRAMIENTAS DE INTEGRACIÓN EXTERNA
            # ═══════════════════════════════════════════════════════════════
            elif tool_name == "get_confirmation_code":
                email = tool_args.get("email")
                if not email:
                    logger.error(f"  RUNNER ERROR: 'email' no presente en arguments: {tool_args}")
                    return (False, "Error: email missing")
                result = self.agent_tools.get_confirmation_code(email)

            else:
                logger.error(f"  RUNNER ERROR: Herramienta desconocida: '{tool_name}'")
                logger.error(f"  RUNNER ERROR: Herramientas válidas: touch_element_by_id, fill_field_by_id, scroll_screen, scroll_in_element, go_back, assert_screen_contains, activate_app, terminate_app, switch_to_app, switch_to_app_keep_background, get_confirmation_code")
                return (False, f"Error: Unknown tool '{tool_name}'")

            elapsed_ms = int((time.time() - start_time) * 1000)
            
            # Verificar resultado
            # Manejar resultados que pueden ser dict (con UI), str, o MiddlewareResult
            result_message = result
            if isinstance(result, dict):
                # Si es dict, extraer el mensaje
                result_message = result.get("message", str(result))
            elif isinstance(result, MiddlewareResult):
                # MiddlewareResult ya tiene un mensaje
                result_message = result.message
            
            if result_message and "Error" in str(result_message):
                logger.error(f"  ❌ Tool call falló ({elapsed_ms}ms): {result_message}")
                return (False, result_message)
            elif result:
                logger.info(f"  ┌─ TOOL CALL ─────────────────────────┐")
                logger.info(f"  │ Tool: {tool_name}")
                logger.info(f"  │ Args: {tool_args}")
                logger.info(f"  │ ID: {tool_id}")
                logger.info(f"  │ Status: Success")
                logger.info(f"  │ Step: {step[:50]}...")
                logger.info(f"  │ Result: {result_message}")
                if isinstance(result, dict) and result.get("ui_elements"):
                    logger.info(f"  │ UI: {len(result['ui_elements'])} elementos disponibles")
                logger.info(f"  │ Duration: {elapsed_ms}ms")
                logger.info(f"  └─────────────────────────────────────────────────┘")
                # Retornar el resultado completo (puede incluir UI)
                return (True, result)
            else:
                # Sin resultado (no debería pasar, pero por seguridad)
                return (False, "Error: No result returned from tool")

        except KeyError as ke:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.error(f"TEST_RUNNER ERROR: Argumento faltante en tool call: {ke}")
            logger.error(f"TEST_RUNNER ERROR: Tool: {tool_name}, Args recibidos: {tool_args}")
            return (False, f"Error: Missing argument {ke}")
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.error(f"TEST_RUNNER ERROR: Excepción ejecutando {tool_name} ({elapsed_ms}ms)")
            logger.error(f"TEST_RUNNER ERROR: {type(e).__name__}: {str(e)}")
            logger.error(f"TEST_RUNNER ERROR: Traceback:\n{traceback.format_exc()}")
            return (False, f"Error: {type(e).__name__}: {str(e)}")

    def clear_history(self):
        """Limpia el historial de acciones."""
        previous_count = len(self.action_history)
        self.action_history = []  # V2: List[Dict[str, Any]]
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
            if isinstance(action, dict):
                logger.info(f"║    - {action.get('action', 'N/A')[:55]}...")
            else:
                logger.info(f"║    - {action[:55]}...")
        logger.info("║")
        logger.info("║  Estado del UIParser:")
        logger.info(f"║    Elementos mapeados: {len(self.ui_parser.element_map)}")
        logger.info(f"║    Próximo ID: {self.ui_parser.current_id}")
        logger.info("╚" + "═" * 60 + "╝")
