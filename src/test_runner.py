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
from typing import List, Optional
from datetime import datetime
from appium.webdriver import Remote

from src.ui_parser import UIParser
from src.agent_tools import AppiumSkills
from src.ai_orchestrator import AIOrchestrator
from src.config import Config

# Importar excepciones de Selenium/Appium para identificar errores recuperables
try:
    from selenium.common.exceptions import (
        TimeoutException,
        NoSuchElementException,
        ElementNotInteractableException,
        StaleElementReferenceException,
        WebDriverException,
    )
    SELENIUM_EXCEPTIONS_AVAILABLE = True
except ImportError:
    SELENIUM_EXCEPTIONS_AVAILABLE = False

# Configurar logging con formato detallado
logging.basicConfig(
    level=logging.DEBUG,  # Cambiado a DEBUG para máxima visibilidad
    format='%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def _is_recoverable_error(exception: Exception) -> bool:
    """
    Determina si un error es recuperable (debe reintentarse) o no recuperable.
    
    Errores NO recuperables (no deben reintentarse):
    - ValueError: Datos inválidos, estructura incorrecta
    - KeyError: Clave faltante en diccionario
    - TypeError: Tipos incorrectos
    - AttributeError: Atributo faltante
    - SyntaxError: Error de sintaxis
    - NameError: Nombre no definido
    - ImportError: Error de importación
    - ConfigurationError: Errores de configuración
    
    Errores SÍ recuperables (deben reintentarse):
    - TimeoutException: Timeouts temporales
    - NoSuchElementException: Elemento no encontrado (puede aparecer después)
    - ElementNotInteractableException: Elemento no interactuable (puede cambiar)
    - StaleElementReferenceException: Referencia obsoleta (puede resolverse)
    - WebDriverException: Algunos errores temporales del driver
    
    Args:
        exception: Excepción a evaluar
        
    Returns:
        True si el error es recuperable (debe reintentarse), False si no
    """
    # Errores NO recuperables - errores de programación/configuración
    non_recoverable_errors = (
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        SyntaxError,
        NameError,
        ImportError,
        IndentationError,
        UnicodeError,
    )
    
    # Verificar si es un error no recuperable
    if isinstance(exception, non_recoverable_errors):
        return False
    
    # Errores recuperables - errores temporales de Appium/Selenium
    if SELENIUM_EXCEPTIONS_AVAILABLE:
        recoverable_errors = (
            TimeoutException,
            NoSuchElementException,
            ElementNotInteractableException,
            StaleElementReferenceException,
        )
        
        if isinstance(exception, recoverable_errors):
            return True
        
        # WebDriverException puede ser recuperable o no, depende del caso
        # Por defecto, lo consideramos recuperable (puede ser temporal)
        if isinstance(exception, WebDriverException):
            # Algunos WebDriverException son no recuperables (ej: driver desconectado)
            error_msg = str(exception).lower()
            non_recoverable_patterns = [
                "session not created",
                "invalid session id",
                "no such session",
                "session deleted",
            ]
            if any(pattern in error_msg for pattern in non_recoverable_patterns):
                return False
            return True
    
    # Por defecto, si no podemos determinar, asumimos que NO es recuperable
    # para evitar loops infinitos con errores desconocidos
    return False


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
        #logger.info("TEST_RUNNER: Imprimiendo configuración...")
        #Config.debug_print_config()
        
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
        # Límites de acciones (desde Config para permitir personalización via .env)
        max_actions_per_step = Config.MAX_ACTIONS_PER_STEP
        max_repeated_action_attempts = Config.MAX_REPEATED_ACTION_ATTEMPTS
        actions_executed = 0
        
        # Tracking de acciones repetidas (inicializar ANTES del loop de reintentos)
        last_action_signature = None
        repeated_action_count = 0
        
        logger.debug(f"TEST_RUNNER: Configuración del paso:")
        logger.debug(f"  - Max acciones por paso: {max_actions_per_step}")
        logger.debug(f"  - Max intentos misma acción: {max_repeated_action_attempts}")
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
                    # FASE 1: Obtener XML ACTUALIZADO del driver (con espera de estabilidad)
                    # ══════════════════════════════════════════════════════════════
                    logger.debug("  │ FASE 1: Obteniendo XML de la pantalla (con espera de estabilidad)...")
                    phase1_start = time.time()
                    try:
                        # Usar get_screen_tree_stable para manejar pantallas de carga
                        xml_source = self.agent_tools.get_screen_tree_stable()
                        phase1_time = int((time.time() - phase1_start) * 1000)
                        logger.debug(f"  │ FASE 1: ✓ XML estable obtenido en {phase1_time}ms ({len(xml_source)} chars)")
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
                            #logger.debug("  │ FASE 2: Elementos disponibles:")
                            #logger.debug(f"  │ {json.dumps(ui_elements, indent=2, ensure_ascii=False)}")
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
                            # Nueva acción diferente, resetear contador
                            repeated_action_count = 1
                            last_action_signature = current_action_signature
                        
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

                        # ══════════════════════════════════════════════════════════════
                        # FASE 5: Esperar a que la UI se estabilice (manejo de loading)
                        # ══════════════════════════════════════════════════════════════
                        logger.debug("  │ FASE 5: Esperando estabilidad de UI post-acción...")
                        phase5_start = time.time()
                        is_stable, wait_time, stability_reason = self.agent_tools.wait_for_ui_stable()
                        phase5_time = int((time.time() - phase5_start) * 1000)
                        
                        if is_stable:
                            logger.debug(f"  │ FASE 5: ✓ UI estable en {phase5_time}ms ({stability_reason})")
                        else:
                            logger.warning(f"  │ FASE 5: ⚠️ UI no estabilizó en {phase5_time}ms ({stability_reason})")
                            # Continuamos de todos modos, el siguiente ciclo verificará el estado

                        # ══════════════════════════════════════════════════════════════
                        # [OPTIMIZACIÓN - ÁREA DE MEJORA POTENCIAL]
                        # OPTIMIZACIÓN: Verificar si la acción ejecutada completa el paso
                        # Para evitar una segunda llamada innecesaria al orquestador
                        # 
                        # TODO/FIXME: Esta optimización funciona pero puede mejorarse.
                        # Limitaciones actuales:
                        # - Usa análisis de palabras clave en el texto del paso (frágil)
                        # - No considera el contexto completo del paso
                        # - Puede fallar con pasos ambiguos o multi-acción
                        #
                        # Alternativas futuras a considerar:
                        # 1. Delegar completamente a la IA para decidir si el paso está completo
                        # 2. Usar un modelo más ligero/simple para esta verificación
                        # 3. Análisis semántico más sofisticado del paso
                        # 4. Sistema de reglas configurables por tipo de paso
                        # 5. Permitir que la IA en la primera llamada indique si el paso
                        #    quedará completo después de ejecutar la acción
                        #
                        # Para identificar este código en el futuro, buscar:
                        # "_check_if_action_completes_step" o "OPTIMIZACIÓN - ÁREA DE MEJORA"
                        # ══════════════════════════════════════════════════════════════
                        step_completed = self._check_if_action_completes_step(
                            tool_call['name'], tool_call.get('arguments', {}), step
                        )
                        
                        if step_completed:
                            logger.info(f"  │ ✓ Acción ejecutada completa el paso directamente")
                            logger.info(f"  │   Evitando segunda consulta al orquestador (optimización)")
                            action_summary = f"Paso completado: {step}"
                            self.action_history.append(action_summary)
                            
                            attempt_elapsed = (datetime.now() - attempt_start).total_seconds()
                            logger.info(f"  └─ Fin loop (paso completado en {attempt_elapsed:.2f}s) ─┘")
                            logger.info(f"└─ FIN INTENTO {attempt} - ÉXITO ─┘")
                            return True
                        
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
                error_type = type(e).__name__
                error_msg = str(e)
                logger.error(f"TEST_RUNNER ERROR: Excepción en intento {attempt}: {error_type}: {error_msg}")
                logger.error(f"TEST_RUNNER ERROR: Traceback completo:\n{traceback.format_exc()}")
                
                # Verificar si el error es recuperable
                is_recoverable = _is_recoverable_error(e)
                
                if not is_recoverable:
                    # Error NO recuperable - no reintentar, fallar inmediatamente
                    logger.error(f"TEST_RUNNER ERROR: Error NO recuperable ({error_type}) - no se reintentará")
                    logger.error(f"TEST_RUNNER ERROR: Este tipo de error no se puede solucionar con reintentos")
                    logger.error(f"TEST_RUNNER ERROR: Revisa la configuración, estructura de datos o código")
                    return False
                
                # Error recuperable - reintentar si quedan intentos
                if attempt < self.max_retries:
                    logger.warning(f"TEST_RUNNER: Error recuperable ({error_type}) - reintentando...")
                    logger.info(f"TEST_RUNNER: Esperando 2s antes de reintentar...")
                    time.sleep(2)
                    continue
                else:
                    logger.error(f"TEST_RUNNER: Se agotaron los {self.max_retries} reintentos para error recuperable")
                    return False

        logger.error(f"TEST_RUNNER: Se agotaron todos los reintentos para el paso {step_index}")
        return False

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
        if action_name == "assert_screen_contains":
            verification_keywords = ["esperar", "verificar", "comprobar", "validar", "confirmar", "revisar"]
            if any(keyword in step_lower for keyword in verification_keywords):
                logger.debug(f"  │ OPTIMIZACIÓN: assert_screen_contains exitoso en paso de verificación → paso completo")
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
                    logger.error(f"TEST_RUNNER ERROR: 'element_id' no presente en arguments: {tool_args}")
                    return False
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
                result = self.agent_tools.fill_field_by_id(element_id, value)

            elif tool_name == "scroll":
                direction = tool_args.get("direction", "down")
                result = self.agent_tools.scroll(direction)

            elif tool_name == "go_back":
                result = self.agent_tools.go_back()

            elif tool_name == "assert_screen_contains":
                text = tool_args.get("text")
                if text is None:
                    logger.error(f"TEST_RUNNER ERROR: 'text' no presente en arguments: {tool_args}")
                    return False
                is_present, message = self.agent_tools.assert_screen_contains(text)
                result = message
                if not is_present:
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    logger.error(f"  ❌ Aserción falló: {message} ({elapsed_ms}ms)")
                    return False

            # ═══════════════════════════════════════════════════════════════
            # HERRAMIENTAS DE GESTIÓN MULTI-APP
            # ═══════════════════════════════════════════════════════════════
            elif tool_name == "activate_app":
                app_package = tool_args.get("app_package")
                if not app_package:
                    logger.error(f"TEST_RUNNER ERROR: 'app_package' no presente en arguments: {tool_args}")
                    return False
                result = self.agent_tools.activate_app(app_package)

            elif tool_name == "terminate_app":
                app_package = tool_args.get("app_package")
                if not app_package:
                    logger.error(f"TEST_RUNNER ERROR: 'app_package' no presente en arguments: {tool_args}")
                    return False
                result = self.agent_tools.terminate_app(app_package)

            elif tool_name == "switch_to_app":
                app_package = tool_args.get("app_package")
                if not app_package:
                    logger.error(f"TEST_RUNNER ERROR: 'app_package' no presente en arguments: {tool_args}")
                    return False
                result = self.agent_tools.switch_to_app(app_package)

            elif tool_name == "switch_to_app_keep_background":
                app_package = tool_args.get("app_package")
                if not app_package:
                    logger.error(f"TEST_RUNNER ERROR: 'app_package' no presente en arguments: {tool_args}")
                    return False
                result = self.agent_tools.switch_to_app_keep_background(app_package)

            else:
                logger.error(f"TEST_RUNNER ERROR: Herramienta desconocida: '{tool_name}'")
                logger.error(f"TEST_RUNNER ERROR: Herramientas válidas: touch_element_by_id, fill_field_by_id, scroll, go_back, assert_screen_contains, activate_app, terminate_app, switch_to_app, switch_to_app_keep_background")
                return False

            elapsed_ms = int((time.time() - start_time) * 1000)
            
            # Verificar resultado
            if result and "Error" in result:
                logger.error(f"  ❌ Tool call falló ({elapsed_ms}ms): {result}")
                return False
            elif result:
                logger.info(f"  ┌─ TOOL CALL ─────────────────────────┐")
                logger.info(f"  │ Tool: {tool_name}")
                logger.info(f"  │ Args: {tool_args}")
                logger.info(f"  │ ID: {tool_id}")
                logger.info(f"  │ Status: Success")
                logger.info(f"  │ Step: {step[:50]}...")
                logger.info(f"  │ Result: {result}")
                logger.info(f"  │ Duration: {elapsed_ms}ms")
                logger.info(f"  └─────────────────────────────────────────────────┘")

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

