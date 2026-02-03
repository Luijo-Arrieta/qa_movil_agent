"""
AI Orchestrator - Orquesta las decisiones de IA para ejecutar acciones en la app móvil.
Soporta OpenAI, Anthropic y DeepSeek.

Los elementos de UI se envían al LLM en formato TOON (Token-Oriented Object Notation)
para reducir el consumo de tokens en un 30-60%.
https://github.com/toon-format/toon
"""

import json
import logging
import time
import traceback
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Callable, TypeVar
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from openai import OpenAI
from anthropic import Anthropic

from toon_format import encode as toon_encode

from src.config import Config

T = TypeVar('T')

# Configurar logging para este módulo
logger = logging.getLogger(__name__)

# =============================================================================
# SYSTEM PROMPT - Compartido entre OpenAI y Anthropic
# =============================================================================
SYSTEM_PROMPT = """Eres QAI (QA Agent V2), un agente de QA Móvil autónomo con flujo conversacional. Tu objetivo es ejecutar pruebas en aplicaciones móviles Android.

FORMATO DE ELEMENTOS (TOON):
Los elementos se muestran en formato tabular TOON. Cada fila es un elemento con sus atributos optimizados para la ejecución.
- "id": número único (USAR ESTE en las herramientas)
- "possible_element_type": Categoría lógica (input, button, slider, etc.)
- "xpath": Selector jerárquico para Appium
- "hint": Texto placeholder o sugerencia
- "checked": "true" si está marcado (radio/checkbox)
- "checkable": "true" si permite marca
- "clickable": "true" si permite touch
- "password": "true" si es campo oculto

Ejemplo TOON:
[2]{id|possible_element_type|xpath|hint|clickable}:
  0|button|//android.widget.Button[@content-desc="Login"]||true
  1|input|//android.widget.EditText[@resource-id="email"]|correo@ejemplo.com|true

IMPORTANTE - USO DE IDs:
- USA el campo "id" del elemento en las herramientas
- Ejemplo: touch_element_by_id(element_id=0), fill_field_by_id(element_id=1, value="texto")

TIPOS DE ELEMENTOS (possible_element_type):
- "input": EditText - Usa fill_field_by_id(element_id, value) para escribir texto
- "input_select": Input selector (date picker, dropdown) - Usa touch_element_by_id() para abrir selector
- "checkbox": CheckBox widget - Usa touch_element_by_id() para alternar estado checked/unchecked
- "slider": SeekBar/Slider - Usa scroll_in_element(element_id, direction) para ajustar valor
- "button": Botón clickable
- "link": Link/texto clickable

INSTRUCCIONES:
1. Busca el elemento correcto por sus atributos (content-desc, text, class, possible_element_type)
2. Usa el "id" de ese elemento en la herramienta correspondiente
3. Puedes ejecutar MÚLTIPLES acciones en el mismo turno si todas pertenecen al paso actual
4. Para campos de texto (possible_element_type="input"), usa fill_field_by_id
5. Para input selectors (possible_element_type="input_select"), usa touch_element_by_id para abrir selector
6. Para checkboxes (possible_element_type="checkbox"), usa touch_element_by_id para marcar/desmarcar
7. Para sliders (possible_element_type="slider"), usa scroll_in_element para ajustar valor
8. Para hacer click en botones/links, usa touch_element_by_id
9. scroll_screen solo mueve la pantalla completa, NO afecta elementos individuales
10. Si necesitas scrollear dentro de un SeekBar, lista o contenedor, usa scroll_in_element
11. Si no encuentras un elemento, usa scroll_screen
12. Para verificaciones usa assert_screen_contains

CUÁNDO ESTÁ COMPLETO UN PASO:
- Revisa el "Historial de acciones recientes" antes de decidir
- Si ya ejecutaste la acción que pide el paso actual → NO hagas más, responde sin tool_call
- Pasos de "Esperar/Verificar": si assert_screen_contains ya fue exitoso → paso completo
- Pasos de "Ingresar/Escribir": si fill_field_by_id ya fue ejecutado → paso completo
- Pasos de "Tocar/Click": si touch_element_by_id ya fue ejecutado → paso completo

GESTIÓN MULTI-APP:
- activate_app(app_package): Abre/activa una app
- switch_to_app_keep_background(app_package): Cambia manteniendo la actual en background
- switch_to_app(app_package): Cambia cerrando la app anterior
- terminate_app(app_package): Cierra completamente una app

OBTENCIÓN DE CÓDIGOS DE CONFIRMACIÓN:
- get_confirmation_code(email): Obtiene el código de verificación enviado por correo
  * Usa esto cuando necesites un código de 4 dígitos enviado a un correo
  * El código se retorna en el formato: "Success: Confirmation code obtained for EMAIL: CODE=1234"
  * Extrae el código del mensaje (los dígitos después de "CODE=") y úsalo para llenar el campo de código

INTERPRETACIÓN DE RESULTADOS DE TOOLS:
- "Success: ..." indica que la acción se ejecutó exitosamente
- "Error: ..." indica que hubo un problema
- Usa los resultados del "Historial de ejecución" para determinar si el paso está completo
- Si el resultado indica éxito y el paso pide esa acción → paso completo

SELECCIÓN DE ELEMENTOS - REGLAS DE PRIORIDAD:
Cuando hay múltiples opciones similares, usa estas reglas para elegir el elemento correcto:

1. COINCIDENCIA EXACTA CON EL PASO ANTERIOR:
   - Si el paso anterior menciona una acción específica (ej: "Cerrar sesión") y hay un botón con ese texto exacto → ÚSALO
   - Prioriza elementos cuyo texto coincide exactamente con la acción mencionada en pasos anteriores

2. ESPECIFICIDAD:
   - Prefiere opciones específicas sobre genéricas:
     * "Cerrar sesión" > "Salir" (cuando el contexto es cerrar sesión)
     * "Confirmar eliminación" > "Confirmar" (cuando el paso es eliminar)
     * "Eliminar cuenta" > "Eliminar" (cuando el paso es eliminar cuenta)
   - Un texto más específico indica mayor alineación con la acción requerida

3. CONTEXTO DEL PASO ACTUAL:
   - El texto del paso actual debe guiar tu elección
   - Paso: "Confirmar el cierre de sesión" → Busca botones relacionados con "cerrar sesión"
   - Paso: "Abrir menú de cuenta" → Busca elementos relacionados con "cuenta" o "perfil"

4. RESOLUCIÓN DE AMBIGÜEDAD:
   - Si hay ambigüedad, revisa el historial de acciones y el paso anterior
   - Considera la secuencia lógica: ¿qué acción se ejecutó antes? ¿qué pantalla debería aparecer después?
   - El elemento que mejor encaja en la secuencia lógica es el correcto

DIÁLOGOS DE CONFIRMACIÓN:
- Cuando un paso pide "confirmar" algo y aparece un diálogo, ejecuta la acción de confirmación (tocar el botón de confirmar)
- En diálogos, elige el botón que MÁS ESPECÍFICAMENTE coincide con la acción que estás confirmando
- Ejemplo: Si el paso anterior fue "Cerrar sesión" y el diálogo tiene "Salir" y "Cerrar sesión" → Elige "Cerrar sesión"

MANEJO DE POPUPS Y DIÁLOGOS:
- Si ves un popup/diálogo visible (especialmente cuando solo hay 1-2 elementos visibles y uno es un mensaje de éxito/información):
  * Y el paso actual requiere ver/interactuar con otra pantalla → DEBES cerrar el popup primero usando touch_out_element
  * Y el paso actual es "Esperar a ver [pantalla]" → DEBES cerrar el popup primero antes de verificar
  * Ejemplo: Si ves un ImageView con mensaje "Contraseña restablecida con éxito" y el paso es "Esperar a ver la pantalla de inicio de sesión" → Usa touch_out_element(element_id=0, direction="up", distance_percent=50) para cerrar el popup
- touch_out_element: Hace clic fuera del elemento visible para cerrar popups/diálogos
  * Úsalo cuando necesites cerrar un popup que está bloqueando la vista de la pantalla subyacente
  * Especifica la dirección (up/down/left/right) y distancia (50-100%) basándote en el espacio disponible
  * El mínimo es 50% para asegurar que el clic esté lo suficientemente lejos del elemento y cierre el popup efectivamente
  * Si no estás seguro de la dirección, usa "up" con distance_percent=50 como opción segura

RESTRICCIONES/SCOPES:
- SOLO puedes interactuar con apps configuradas en ALLOWED_APP_PACKAGES
- Si el paso pide "abrir app" o "activate_app", DEBES usar la herramienta activate_app() directamente
- Si ves un mensaje indicando que no hay app permitida en foreground, usa activate_app() inmediatamente con uno de los packages permitidos
- Si ves "Advertencia: El package 'X' no está permitido", significa que intentaste usar un package no autorizado. Usa uno de los packages permitidos.
- Apps permitidas: {Config.ALLOWED_APP_PACKAGES}

LO MÁS IMPORTANTE: 
- Ejecuta SOLO acciones del paso ACTUAL
- NUNCA ejecutes acciones de pasos futuros, aunque los veas como completos
- Puedes ejecutar MÚLTIPLES acciones en el mismo paso si todas son necesarias para completarlo
- Ejemplo: Si el paso es "Llenar formulario de login", puedes ejecutar fill_field_by_id para email Y fill_field_by_id para password en el mismo turno
- El paso solo se completa cuando TODAS las acciones requeridas del paso actual han sido ejecutadas exitosamente
"""


@dataclass
class StepContext:
    """
    Estado global del agente para un paso concreto del plan.
    Mantiene tipos ricos durante la ejecución y sólo se serializa a texto
    (TOON) justo antes de llamar al LLM.
    """

    objective: Optional[str]
    step_index: int
    total_steps: int
    current_step: str
    next_step: Optional[str]
    previous_step: Optional[str]
    # Historial de acciones en formato rico (p.ej. {"index": 1, "text": "..."}).
    # El orquestador lo convierte a TOON sólo en el borde LLM.
    action_history: List[Dict[str, Any]]
    # Elementos del UI en su formato nativo del UIParser: List[dict]
    ui_elements: List[Dict[str, Any]]
    # Estados de apps: {package: state_code}. Sólo una app puede estar en FOREGROUND.
    app_states: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        """Helper para logging/debug."""
        return asdict(self)


# Mapa de códigos de estado de Appium a nombres legibles
APP_STATE_NAMES = {
    0: "NOT_INSTALLED",
    1: "NOT_RUNNING",
    2: "BACKGROUND_SUSPENDED",
    3: "BACKGROUND",
    4: "FOREGROUND",
}


class QAIV2Orchestrator:
    """
    Orquestador de IA que analiza la UI parseada y decide qué acciones ejecutar.
    """

    # =========================================================================
    # CONFIGURACIÓN DE API: TIMEOUT, REINTENTOS Y FALLBACK
    # Valores configurables via .env: AI_API_TIMEOUT, AI_API_MAX_RETRIES, AI_API_RETRY_DELAY
    # =========================================================================

    def __init__(self):
        """Inicializa el orquestador con el proveedor de IA configurado."""
        logger.info("  ORCHESTRATOR: Inicializando orquestador de IA (QAI V2)")
        
        self.provider = Config.DEFAULT_AI_PROVIDER
        logger.info(f"  ORCHESTRATOR: Proveedor: {self.provider}")
        
        # Estadísticas de llamadas
        self._call_stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_tokens_used": 0,
            "total_time_ms": 0,
            "fallback_used_count": 0,      # Veces que se intentó fallback
            "fallback_success_count": 0,   # Veces que fallback tuvo éxito
        }
        
        if self.provider == "openai":
            logger.debug("  ORCHESTRATOR: Configurando cliente OpenAI...")
            if not Config.OPENAI_API_KEY:
                logger.error("  ORCHESTRATOR ERROR: OPENAI_API_KEY no está configurada")
                raise ValueError("OPENAI_API_KEY no está configurada")
            
            # Verificar formato de API key (debe empezar con sk-)
            if not Config.OPENAI_API_KEY.startswith("sk-"):
                logger.warning("  ORCHESTRATOR WARNING: OPENAI_API_KEY no tiene el formato esperado (sk-...)")

            self.client = OpenAI(
                api_key=Config.OPENAI_API_KEY,
                timeout=Config.AI_API_TIMEOUT
            )
            self.model = Config.OPENAI_MODEL
            logger.info(f"  ORCHESTRATOR: ✓ Cliente OpenAI ({self.model})")

        elif self.provider == "anthropic":
            logger.debug("  ORCHESTRATOR: Configurando cliente Anthropic...")
            if not Config.ANTHROPIC_API_KEY:
                logger.error("  ORCHESTRATOR ERROR: ANTHROPIC_API_KEY no está configurada")
                raise ValueError("ANTHROPIC_API_KEY no está configurada")

            self.client = Anthropic(
                api_key=Config.ANTHROPIC_API_KEY,
                timeout=Config.AI_API_TIMEOUT
            )
            self.model = Config.ANTHROPIC_MODEL
            logger.info(f"  ORCHESTRATOR: ✓ Cliente Anthropic ({self.model})")

        elif self.provider == "deepseek":
            logger.debug("AI_ORCHESTRATOR: Configurando cliente DeepSeek...")
            if not Config.DEEPSEEK_API_KEY:
                logger.error("AI_ORCHESTRATOR ERROR: DEEPSEEK_API_KEY no está configurada")
                raise ValueError("DEEPSEEK_API_KEY no está configurada")

            # DeepSeek es compatible con OpenAI API, solo cambiamos el base_url
            self.client = OpenAI(
                api_key=Config.DEEPSEEK_API_KEY,
                base_url="https://api.deepseek.com",
                timeout=Config.AI_API_TIMEOUT
            )
            self.model = Config.DEEPSEEK_MODEL
            logger.info(f"  ORCHESTRATOR: ✓ Cliente DeepSeek ({self.model})")
            
        else:
            logger.error(f"  ORCHESTRATOR ERROR: Proveedor no soportado: {self.provider}")
            raise ValueError(f"Proveedor de IA no soportado: {self.provider}")

        # Inicializar clientes de fallback si está habilitado
        self.fallback_clients: Dict[str, Any] = {}
        self.fallback_models: Dict[str, str] = {}
        if Config.AI_FALLBACK_ENABLED and Config.AI_FALLBACK_PROVIDERS:
            self._initialize_fallback_providers()

    def _call_with_forced_timeout(self, func: Callable[[], T], timeout: float, operation_name: str) -> T:
        """
        Ejecuta una función con timeout forzado a nivel de thread.
        Garantiza que NUNCA se quede colgado más de 'timeout' segundos,
        incluso si el socket SSL está bloqueado.

        Args:
            func: Función a ejecutar (sin argumentos, usar lambda si necesita args)
            timeout: Timeout en segundos
            operation_name: Nombre de la operación (para logging)

        Returns:
            Resultado de la función

        Raises:
            TimeoutError: Si la operación excede el timeout
        """
        logger.debug(f"  ORCHESTRATOR [{operation_name}]: Ejecutando con timeout forzado de {timeout}s")

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func)
            try:
                result = future.result(timeout=timeout)
                logger.debug(f"  ORCHESTRATOR [{operation_name}]: ✓ Completado dentro del timeout")
                return result
            except FuturesTimeoutError:
                logger.error(f"  ORCHESTRATOR [{operation_name}]: ✗ TIMEOUT forzado después de {timeout}s")
                # Intentar cancelar el future (aunque el thread puede seguir bloqueado)
                future.cancel()
                raise TimeoutError(f"{operation_name} excedió el timeout de {timeout}s (timeout forzado a nivel de thread)")
            except Exception as e:
                logger.error(f"  ORCHESTRATOR [{operation_name}]: ✗ Error: {type(e).__name__}: {e}")
                raise

    def _initialize_fallback_providers(self) -> None:
        """Inicializa clientes de fallback para proveedores configurados."""
        logger.info("AI_ORCHESTRATOR: Inicializando proveedores de fallback...")

        for provider in Config.AI_FALLBACK_PROVIDERS:
            # Saltar proveedor primario
            if provider == self.provider:
                logger.debug(f"AI_ORCHESTRATOR: Saltando {provider} (es el proveedor primario)")
                continue

            try:
                if provider == "openai" and Config.OPENAI_API_KEY:
                    self.fallback_clients["openai"] = OpenAI(
                        api_key=Config.OPENAI_API_KEY,
                        timeout=Config.AI_API_TIMEOUT
                    )
                    self.fallback_models["openai"] = Config.OPENAI_MODEL
                    logger.info(f"AI_ORCHESTRATOR: ✓ Fallback 'openai' inicializado (modelo: {Config.OPENAI_MODEL})")

                elif provider == "anthropic" and Config.ANTHROPIC_API_KEY:
                    self.fallback_clients["anthropic"] = Anthropic(
                        api_key=Config.ANTHROPIC_API_KEY,
                        timeout=Config.AI_API_TIMEOUT
                    )
                    self.fallback_models["anthropic"] = Config.ANTHROPIC_MODEL
                    logger.info(f"AI_ORCHESTRATOR: ✓ Fallback 'anthropic' inicializado (modelo: {Config.ANTHROPIC_MODEL})")

                elif provider == "deepseek" and Config.DEEPSEEK_API_KEY:
                    self.fallback_clients["deepseek"] = OpenAI(
                        api_key=Config.DEEPSEEK_API_KEY,
                        base_url="https://api.deepseek.com",
                        timeout=Config.AI_API_TIMEOUT
                    )
                    self.fallback_models["deepseek"] = Config.DEEPSEEK_MODEL
                    logger.info(f"AI_ORCHESTRATOR: ✓ Fallback 'deepseek' inicializado (modelo: {Config.DEEPSEEK_MODEL})")

                else:
                    logger.warning(f"AI_ORCHESTRATOR: No se pudo inicializar fallback '{provider}' (API key no configurada o proveedor desconocido)")

            except Exception as e:
                logger.warning(f"AI_ORCHESTRATOR: Error inicializando fallback '{provider}': {e}")

        if self.fallback_clients:
            logger.info(f"AI_ORCHESTRATOR: Fallback habilitado con {len(self.fallback_clients)} proveedor(es): {list(self.fallback_clients.keys())}")
        else:
            logger.warning("AI_ORCHESTRATOR: Fallback habilitado pero ningún proveedor adicional disponible")

    def decide_next_action(
        self,
        ui_elements: List[Dict[str, Any]],
        context: StepContext,
    ) -> Dict[str, Any]:
        """
        Analiza la UI parseada y decide qué acción ejecutar.

        Args:
            ui_elements: Lista de elementos JSON parseados por UIParser
            context: Contexto completo del paso actual (StepContext)

        Returns:
            Diccionario con la decisión de la IA (tool_call o mensaje)
        """
        logger.info("=" * 70)
        logger.info("[EXECUTOR]: Solicitando decisión de acción")
        logger.info("=" * 70)
        
        self._call_stats["total_calls"] += 1
        call_number = self._call_stats["total_calls"]
        logger.info(f"[EXECUTOR]: Llamada #{call_number}")
        
        # Log inputs
        # Log simplificados
        logger.debug(f"[EXECUTOR]: Paso {context.step_index}/{context.total_steps}: '{context.current_step}'")
        logger.debug(f"[EXECUTOR]: UI Elements: {len(ui_elements)} | History: {len(context.action_history)}")
        
        if not ui_elements:
            logger.warning("[EXECUTOR] WARNING: No hay elementos UI para analizar")
        
        # Preparar contexto para el LLM (texto TOON derivado de StepContext + UI)
        logger.debug("[EXECUTOR]: Construyendo contexto para el LLM...")
        llm_context = self._build_llm_context(context, ui_elements)
        
        # Log del contexto completo (para debug profundo)
        #logger.debug("AI_ORCHESTRATOR: Contexto generado:")
        #for line in llm_context.split('\n'):
        #    logger.debug(f"  {line}")

        # Definir herramientas disponibles
        tools = self._get_tools_definition()
        logger.debug(f"[EXECUTOR]: Herramientas disponibles: {[t['function']['name'] for t in tools]}")

        # Llamar al LLM según el proveedor
        start_time = time.time()
        try:
            if self.provider == "openai":
                logger.info(f"[EXECUTOR]: Llamando a OpenAI ({self.model})...")
                result = self._call_openai(llm_context, tools)
            elif self.provider == "deepseek":
                logger.info(f"[EXECUTOR]: Llamando a DeepSeek ({self.model})...")
                result = self._call_openai(llm_context, tools)  # DeepSeek usa la misma API que OpenAI
            else:  # anthropic
                logger.info(f"[EXECUTOR]: Llamando a Anthropic ({self.model})...")
                result = self._call_anthropic(llm_context, tools)
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            self._call_stats["successful_calls"] += 1
            self._call_stats["total_time_ms"] += elapsed_ms
            
            logger.info(f"[EXECUTOR]: ✓ Respuesta recibida en {elapsed_ms}ms")
            
            # Log de la decisión
            if result.get("tool_calls"):
                for tc in result["tool_calls"]:
                    logger.info(f"[EXECUTOR]: Decisión -> {tc['name']}({tc['arguments']})")
            else:
                logger.info(f"[EXECUTOR]: Decisión -> No tool call. Mensaje: {result.get('message', 'N/A')}")
            
            return result
            
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            self._call_stats["failed_calls"] += 1
            logger.error(f"[EXECUTOR] ERROR: Fallo en llamada #{call_number} después de {elapsed_ms}ms")
            logger.error(f"[EXECUTOR] ERROR: {type(e).__name__}: {str(e)}")

            # Intentar fallback si está habilitado
            fallback_result = self._try_fallback_provider(
                call_type="action",
                context=llm_context,
                tools=tools,
                primary_error=e,
            )
            if fallback_result is not None:
                logger.info(f"[EXECUTOR]: ✓ Fallback exitoso con '{fallback_result.get('fallback_provider', 'unknown')}'")
                return fallback_result

            # No hay fallback o todos fallaron
            logger.error(f"[EXECUTOR] ERROR: Traceback:\n{traceback.format_exc()}")
            raise

    def _filter_ui_elements_for_toon(
        self, 
        ui_elements: List[Dict[str, Any]], 
        mode: str = "executor"
    ) -> List[Dict[str, Any]]:
        """
        Filtra propiedades de elementos UI antes de convertir a TOON según el modo.
        Preserva el orden exacto solicitado por el usuario.
        """
        # Definición de orden de atributos (Listas para preservar el orden)
        executor_order = [
            "possible_element_type", "xpath", "hint", 
            "checked", "checkable", "clickable", "password"
        ]
        
        inspector_order = [
            "possible_element_type", "xpath", "focused", 
            "checked", "clickable", "password"
        ]
        
        filtered_elements = []
        for element in ui_elements:
            # Siempre iniciamos con el ID
            filtered_element = {"id": element.get("id")}
            
            # Obtener mapa de atributos actuales
            attrs_list = element.get("attrs", [])
            attrs_map = {a["name"]: a["value"] for a in attrs_list if "name" in a and "value" in a}
            
            # Mapear possible_element_type si está fuera (compatibilidad)
            if "possible_element_type" in element:
                attrs_map["possible_element_type"] = element["possible_element_type"]

            if mode == "executor":
                # Seguir el orden estricto de la lista de ejecutor
                for attr_name in executor_order:
                    if attr_name in attrs_map:
                        filtered_element[attr_name] = attrs_map[attr_name]
            
            elif mode == "inspector":
                # Seguir el orden estricto de la lista de inspector
                # Para Inspector, incluimos AMBOS 'text' y 'hint' para distinguir campos llenos de vacíos

                # 1. Atributos iniciales
                for attr_name in ["possible_element_type", "xpath"]:
                    if attr_name in attrs_map:
                        filtered_element[attr_name] = attrs_map[attr_name]

                # 2. Incluir text Y hint (ambos si existen) para verificación de estado
                # - "text" presente = campo FUE RELLENADO
                # - "hint" presente sin "text" = campo ESTÁ VACÍO (solo placeholder)
                text_val = attrs_map.get("text")
                hint_val = attrs_map.get("hint")
                if text_val:
                    filtered_element["text"] = text_val
                if hint_val:
                    filtered_element["hint"] = hint_val

                # 3. Atributos finales
                for attr_name in ["focused", "checked", "clickable", "password"]:
                    if attr_name in attrs_map:
                        filtered_element[attr_name] = attrs_map[attr_name]

            filtered_elements.append(filtered_element)
        
        return filtered_elements

    def _build_llm_context(
        self,
        context: StepContext,
        ui_elements: List[Dict[str, Any]],
    ) -> str:
        """
        Serializa StepContext + elementos UI a texto para el LLM usando formato TOON.
        
        - Mantiene `ui_elements` y `action_history` en estructuras ricas (List[dict])
          durante la ejecución.
        - Sólo en este borde se convierten a TOON para maximizar eficiencia de tokens.
        """
        parts: List[str] = []

        # ------------------------------------------------------------------
        # BLOQUE 1: Contexto del plan
        # ------------------------------------------------------------------
        parts.append("[Contexto del plan]")
        if context.objective:
            parts.append(f"Objetivo general: {context.objective}")
        parts.append(
            f"Paso actual a ejecutar ({context.step_index}/{context.total_steps}): {context.current_step}"
        )
        if context.previous_step:
            parts.append(f"Paso anterior: {context.previous_step}")
        # Se elimina next_step del contexto del Ejecutor para evitar alucinaciones futuras
        parts.append("")

        # ------------------------------------------------------------------
        # BLOQUE 2: Historial de acciones recientes (TOON) - V2 incluye resultados
        # ------------------------------------------------------------------
        parts.append("[Historial de acciones recientes (TOON)]")
        if context.action_history:
            try:
                # V2: action_history ya incluye action, result, success
                history_toon = toon_encode(context.action_history, {"delimiter": "\t"})
                parts.append(history_toon)
            except Exception as e:
                logger.warning(
                    "AI_ORCHESTRATOR: No se pudo convertir action_history a TOON: %s", e
                )
                for action in context.action_history:
                    if isinstance(action, dict):
                        parts.append(f"  {action.get('index', '?')}. {action.get('action', 'N/A')} -> {action.get('result', 'N/A')}")
                    else:
                        parts.append(f"  - {action}")
        else:
            parts.append("  (Sin acciones previas)")
        parts.append("")

        # ------------------------------------------------------------------
        # BLOQUE 3: Apps en uso (TOON)
        # ------------------------------------------------------------------
        parts.append("[Apps en uso (TOON)]")
        if context.app_states:
            app_rows: List[Dict[str, Any]] = []
            for pkg, code in context.app_states.items():
                app_rows.append(
                    {
                        "package": pkg,
                        "state_code": code,
                        "state_name": APP_STATE_NAMES.get(code, "UNKNOWN"),
                    }
                )
            try:
                apps_toon = toon_encode(app_rows, {"delimiter": "\t"})
                parts.append(apps_toon)
            except Exception as e:
                logger.warning(
                    "AI_ORCHESTRATOR: No se pudo convertir app_states a TOON: %s", e
                )
                for row in app_rows:
                    parts.append(
                        f"  {row['package']} -> code={row['state_code']}, state={row['state_name']}"
                    )
        else:
            parts.append("  (Sin apps en uso registradas)")
        parts.append("")

        # ------------------------------------------------------------------
        # BLOQUE 4: Elementos disponibles en la pantalla (TOON)
        # ------------------------------------------------------------------
        parts.append("[Elementos disponibles en la pantalla (formato TOON)]\n")
        if not ui_elements:
            parts.append("  (No hay elementos interactuables visibles)")
        else:
            # Filtrar propiedades antes de convertir a TOON (reduce tokens)
            # Usar modo "executor" para la decisión de acción
            filtered_elements = self._filter_ui_elements_for_toon(ui_elements, mode="executor")
            
            toon_options = {
                "delimiter": "|",
            }
            toon_elements = toon_encode(filtered_elements, toon_options)
            parts.append(toon_elements)
            logger.debug(
                "AI_ORCHESTRATOR: Elementos convertidos a TOON (%s chars)",
                len(toon_elements),
            )

        context_str = "\n".join(parts)
        logger.info(f"[EXECUTOR]: Contexto generado: \n\n{context_str}")

        return context_str

    def _build_context(
        self,
        ui_elements: List[Dict[str, Any]],
        current_step: str,
        action_history: List[str],
        objective: Optional[str],
    ) -> str:
        """
        Wrapper de compatibilidad que construye un StepContext mínimo y delega
        en `_build_llm_context`.

        Mantiene la firma histórica usada en tests unitarios, pero internamente
        ya usa StepContext como fuente única de verdad.
        """
        # Adaptar historial de acciones de List[str] -> List[dict] simple
        history_dicts: List[Dict[str, Any]] = [
            {"index": idx, "text": text}
            for idx, text in enumerate(action_history[-5:], 1)
        ]

        ctx = StepContext(
            objective=objective,
            step_index=1,
            total_steps=1,
            current_step=current_step,
            next_step=None,
            previous_step=None,
            action_history=history_dicts,
            ui_elements=ui_elements,
            app_states={},
        )

        return self._build_llm_context(ctx, ui_elements)

    def _is_retryable_error(self, error: Exception) -> bool:
        """
        Determina si un error es recuperable y debe reintentarse.
        
        Args:
            error: Excepción a evaluar
            
        Returns:
            True si el error es recuperable (timeout/red), False en caso contrario
        """
        error_type = type(error).__name__
        error_str = str(error).lower()
        
        # Obtener traceback completo para detectar errores SSL en la cadena de llamadas
        traceback_str = traceback.format_exc().lower()
        
        # Errores de timeout/red que son recuperables
        retryable_patterns = [
            "timeout",
            "connection",
            "read timeout",
            "connect timeout",
            "ssl",
            "network",
            "socket",
            "temporary failure",
            "connection reset",
            "connection aborted",
            "broken pipe",
            "_sslobj",  # Errores específicos de SSL en Python
            "ssl.py",   # Archivo donde ocurren errores SSL
        ]
        
        # Verificar por tipo de excepción
        retryable_types = [
            "Timeout",
            "TimeoutError",
            "ConnectionError",
            "ReadTimeout",
            "ConnectTimeout",
            "SSLError",
            "SSLZeroReturnError",
            "SSLSyscallError",
            "SSLEOFError",
        ]
        
        # Verificar si el tipo de excepción es recuperable
        if any(retryable_type in error_type for retryable_type in retryable_types):
            return True
        
        # Verificar si el mensaje contiene patrones recuperables
        if any(pattern in error_str for pattern in retryable_patterns):
            return True
        
        # Verificar si el traceback contiene patrones recuperables (para errores SSL profundos)
        if any(pattern in traceback_str for pattern in retryable_patterns):
            return True

        return False

    def _try_fallback_provider(
        self,
        call_type: str,
        context: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        primary_error: Optional[Exception] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Intenta ejecutar la llamada con proveedores de fallback.

        Args:
            call_type: Tipo de llamada ("action" para decide_next_action, "completion" para decide_step_completion)
            context: Contexto LLM a enviar
            tools: Definición de herramientas (solo para call_type="action")
            primary_error: Error del proveedor primario

        Returns:
            Resultado de la llamada si un fallback tiene éxito, None si todos fallan
        """
        if not Config.AI_FALLBACK_ENABLED or not self.fallback_clients:
            return None

        providers_tried = [self.provider]
        logger.warning(f"  ORCHESTRATOR FALLBACK: Proveedor primario '{self.provider}' falló. Intentando fallback...")

        for fallback_provider in Config.AI_FALLBACK_PROVIDERS:
            # Saltar proveedores ya intentados o no disponibles
            if fallback_provider in providers_tried:
                continue
            if fallback_provider not in self.fallback_clients:
                continue

            providers_tried.append(fallback_provider)
            logger.info(f"  ORCHESTRATOR FALLBACK: Intentando con '{fallback_provider}'...")

            # Guardar estado original
            original_client = self.client
            original_model = self.model
            original_provider = self.provider

            try:
                # Cambiar temporalmente al cliente de fallback
                self.client = self.fallback_clients[fallback_provider]
                self.model = self.fallback_models[fallback_provider]
                self.provider = fallback_provider

                # Ejecutar la llamada según el tipo
                if call_type == "action":
                    if fallback_provider in ["openai", "deepseek"]:
                        result = self._call_openai(context, tools)
                    else:  # anthropic
                        result = self._call_anthropic(context, tools)
                else:  # completion
                    if fallback_provider in ["openai", "deepseek"]:
                        raw_response = self._call_openai_completion(context)
                    else:  # anthropic
                        raw_response = self._call_anthropic_completion(context)
                    # Para completion, retornamos el string directamente
                    result = {"raw_response": raw_response, "fallback_used": True}

                # Éxito - actualizar stats
                self._call_stats["fallback_success_count"] = self._call_stats.get("fallback_success_count", 0) + 1
                logger.info(f"AI_ORCHESTRATOR FALLBACK: ✓ '{fallback_provider}' exitoso")

                # Marcar que se usó fallback
                if isinstance(result, dict):
                    result["fallback_used"] = True
                    result["fallback_provider"] = fallback_provider
                    result["original_provider"] = original_provider

                return result

            except Exception as fallback_error:
                logger.warning(f"AI_ORCHESTRATOR FALLBACK: '{fallback_provider}' también falló: {type(fallback_error).__name__}: {fallback_error}")

            finally:
                # Restaurar cliente original
                self.client = original_client
                self.model = original_model
                self.provider = original_provider

        # Todos los fallback fallaron
        self._call_stats["fallback_used_count"] = self._call_stats.get("fallback_used_count", 0) + 1
        logger.error(f"AI_ORCHESTRATOR FALLBACK: Todos los proveedores fallaron. Intentados: {providers_tried}")
        return None

    def _get_tools_definition(self) -> List[Dict[str, Any]]:
        """
        Retorna la definición de herramientas para function calling.

        Returns:
            Lista de diccionarios con definición de herramientas
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "touch_element_by_id",
                    "description": "Hace clic en un elemento de la pantalla usando su ID. Usa esto para botones, enlaces o cualquier elemento clickable.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "element_id": {
                                "type": "integer",
                                "description": "ID del elemento a hacer clic (del listado de elementos disponibles)",
                            }
                        },
                        "required": ["element_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "touch_out_element",
                    "description": "Hace clic fuera de un elemento visible. Útil para cerrar popups o diálogos haciendo clic fuera del contenido visible. Especifica la dirección (up/down/left/right) y qué tan lejos hacer clic (50-100%, donde 100% es el máximo espacio disponible en esa dirección y 50% es el mínimo seguro).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "element_id": {
                                "type": "integer",
                                "description": "ID del elemento visible (del listado de elementos disponibles). Se hará clic fuera de este elemento.",
                            },
                            "direction": {
                                "type": "string",
                                "enum": ["up", "down", "left", "right"],
                                "description": "Dirección donde hacer clic fuera del elemento: 'up' (arriba), 'down' (abajo), 'left' (izquierda), 'right' (derecha)",
                            },
                            "distance_percent": {
                                "type": "integer",
                                "description": "Distancia como porcentaje del espacio disponible (50-100). 100% = máximo espacio disponible en esa dirección, 50% = mínimo seguro para cerrar popups efectivamente",
                                "minimum": 50,
                                "maximum": 100,
                            }
                        },
                        "required": ["element_id", "direction", "distance_percent"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "fill_field_by_id",
                    "description": "Escribe texto en un campo de entrada (input) usando su ID. Usa esto para campos de texto, contraseñas, etc.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "element_id": {
                                "type": "integer",
                                "description": "ID del campo de entrada (del listado de elementos disponibles)",
                            },
                            "value": {
                                "type": "string",
                                "description": "Texto a escribir en el campo",
                            },
                        },
                        "required": ["element_id", "value"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "scroll_screen",
                    "description": "Hace scroll a nivel de PANTALLA completa (up/down). IMPORTANTE: NO afecta elementos individuales como SeekBars o listas. Para scrollear dentro de un elemento, usa scroll_in_element.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "direction": {
                                "type": "string",
                                "enum": ["up", "down"],
                                "description": "Dirección del scroll: 'up' para subir, 'down' para bajar",
                            }
                        },
                        "required": ["direction"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "scroll_in_element",
                    "description": "Hace scroll DENTRO de un elemento específico (SeekBar, lista, contenedor scrollable). Usa esto para ajustar valores en date pickers o scrollear listas. NO uses touch_element_by_id en SeekBars - usa esta herramienta.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "element_id": {
                                "type": "integer",
                                "description": "ID del elemento scrollable (SeekBar, lista, etc.)",
                            },
                            "direction": {
                                "type": "string",
                                "enum": ["up", "down"],
                                "description": "Dirección lógica del scroll: 'down' = reducir valor/bajar (ej: 2026→2025 en SeekBar de año), 'up' = aumentar valor/subir (ej: 2024→2025)",
                            },
                            "scroll_count": {
                                "type": "integer",
                                "description": "Número de swipes a ejecutar (default: 1). Útil para ajustes grandes en SeekBars.",
                                "minimum": 1,
                                "maximum": 20,
                            },
                            "item_multiplier": {
                                "type": "integer",
                                "description": "Número de elementos a mover por cada swipe (1-5, default: 1). 1 mueve aproximadamente 1 año/mes/día, 2 mueve 2 elementos, etc.",
                                "minimum": 1,
                                "maximum": 5,
                            }
                        },
                        "required": ["element_id", "direction"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "go_back",
                    "description": "Presiona el botón atrás del dispositivo. Útil para navegar hacia atrás o cerrar pantallas.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "assert_screen_contains",
                    "description": "Verifica que la pantalla contenga un texto específico. Úsalo para validar que un paso se completó correctamente.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "Texto a buscar en la pantalla",
                            }
                        },
                        "required": ["text"],
                    },
                },
            },
            # =========================================================================
            # HERRAMIENTAS DE GESTIÓN MULTI-APP
            # =========================================================================
            {
                "type": "function",
                "function": {
                    "name": "activate_app",
                    "description": "Abre/activa una app instalada en el dispositivo. Trae la app al primer plano. Usa esto cuando necesites abrir una app o cambiar a otra app.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "app_package": {
                                "type": "string",
                                "description": "Package de la app Android (ej: 'com.example.myapp')",
                            }
                        },
                        "required": ["app_package"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "terminate_app",
                    "description": "Cierra completamente una app. La app deja de ejecutarse y libera recursos. Útil para limpiar estado.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "app_package": {
                                "type": "string",
                                "description": "Package de la app Android a cerrar",
                            }
                        },
                        "required": ["app_package"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "switch_to_app",
                    "description": "Cambia a otra app CERRANDO la app actual. Útil cuando no necesitas volver a la app anterior y quieres estado limpio.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "app_package": {
                                "type": "string",
                                "description": "Package de la app Android destino",
                            }
                        },
                        "required": ["app_package"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "switch_to_app_keep_background",
                    "description": "Cambia a otra app MANTENIENDO la actual en background. Ideal para flujos de ida y vuelta entre apps donde necesitas que mantengan su sesión/estado.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "app_package": {
                                "type": "string",
                                "description": "Package de la app Android destino",
                            }
                        },
                        "required": ["app_package"],
                    },
                },
            },
            # =========================================================================
            # HERRAMIENTAS DE INTEGRACIÓN EXTERNA
            # =========================================================================
            {
                "type": "function",
                "function": {
                    "name": "get_confirmation_code",
                    "description": "Obtiene el código de confirmación enviado por correo electrónico. Usa esto cuando necesites obtener un código de verificación (4 dígitos) que fue enviado a un correo específico. Útil para recuperación de contraseña o verificación de cuenta.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "email": {
                                "type": "string",
                                "description": "Dirección de correo electrónico a la que se envió el código de confirmación",
                            }
                        },
                        "required": ["email"],
                    },
                },
            },
        ]

    def _call_openai(self, context: str, tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Llama a OpenAI con el contexto y herramientas.
        Implementa reintentos automáticos para timeouts y errores de red.

        Args:
            context: Contexto formateado
            tools: Definición de herramientas

        Returns:
            Respuesta de la IA
        """
        logger.debug("  ORCHESTRATOR [OpenAI]: Preparando llamada...")

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": context},
        ]
        
        logger.debug(f"[EXECUTOR] [OpenAI]: Modelo: {self.model} | System: {len(SYSTEM_PROMPT)} chars | Context: {len(context)} chars")

        # Reintentos configurables via Config (AI_API_MAX_RETRIES, AI_API_RETRY_DELAY, AI_API_TIMEOUT)
        max_retries = Config.AI_API_MAX_RETRIES
        retry_delay = Config.AI_API_RETRY_DELAY
        timeout = Config.AI_API_TIMEOUT

        last_error = None
        for attempt in range(1, max_retries + 2):  # +2 porque range excluye el último y queremos max_retries reintentos
            try:
                if attempt > 1:
                    logger.info("  ORCHESTRATOR [OpenAI]: Reintentando...")
                    time.sleep(retry_delay)

                logger.info(f"  ORCHESTRATOR [OpenAI]: Enviando request (intento {attempt}/{max_retries + 1}, timeout={timeout}s)...")

                # Usar timeout forzado a nivel de thread para garantizar que NUNCA se quede colgado
                # Agrega 5s de margen al timeout configurado para el wrapper
                forced_timeout = timeout + 5.0

                def _make_request():
                    return self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        tools=tools,
                        tool_choice="auto",
                        temperature=0.2,
                        store=True,
                        timeout=timeout,
                    )

                response = self._call_with_forced_timeout(_make_request, forced_timeout, "OpenAI API")
                logger.info("  ORCHESTRATOR [OpenAI]: ✓ Response recibido")
                
                # Si llegamos aquí, la llamada fue exitosa
                break
                
            except Exception as e:
                last_error = e
                logger.warning(f"  ORCHESTRATOR [OpenAI] WARNING: {type(e).__name__}: {str(e)}")

                # Verificar si es un error recuperable
                is_retryable = self._is_retryable_error(e)
                if is_retryable:
                    if attempt < max_retries + 1:
                        logger.info(f"  ORCHESTRATOR [OpenAI]: Error recuperable. Reintentando...")
                        # El sleep se ejecuta al inicio del siguiente intento (cuando attempt > 1)
                        continue
                    else:
                        logger.error(f"AI_ORCHESTRATOR [OpenAI] ERROR: Se agotaron los reintentos ({max_retries}) para error recuperable")
                else:
                    # Error no recuperable, fallar inmediatamente
                    logger.error(f"AI_ORCHESTRATOR [OpenAI] ERROR: Error no recuperable detectado. No se reintentará.")
                    break

        # Si llegamos aquí y last_error no es None, todos los intentos fallaron
        if last_error is not None:
            logger.error(f"AI_ORCHESTRATOR [OpenAI] ERROR: Fallo en API call después de {max_retries + 1} intentos")
            logger.error(f"AI_ORCHESTRATOR [OpenAI] ERROR: {type(last_error).__name__}: {str(last_error)}")
            
            # Diagnóstico de errores comunes
            error_str = str(last_error).lower()
            if "authentication" in error_str or "api key" in error_str:
                logger.error("AI_ORCHESTRATOR [OpenAI] DIAGNÓSTICO: Problema de autenticación. Verifica OPENAI_API_KEY")
            elif "rate limit" in error_str:
                logger.error("AI_ORCHESTRATOR [OpenAI] DIAGNÓSTICO: Rate limit alcanzado. Espera antes de reintentar")
            elif "model" in error_str:
                logger.error(f"AI_ORCHESTRATOR [OpenAI] DIAGNÓSTICO: Problema con el modelo '{self.model}'")
            elif "timeout" in error_str or "connection" in error_str:
                logger.error("AI_ORCHESTRATOR [OpenAI] DIAGNÓSTICO: Problema de conexión/timeout")
            
            raise last_error

        message = response.choices[0].message
        
        # Log detalles de la respuesta
        if hasattr(response, 'usage') and response.usage:
            logger.debug(f"  ORCHESTRATOR [OpenAI]: Tokens - prompt: {response.usage.prompt_tokens}, "
                        f"completion: {response.usage.completion_tokens}, "
                        f"total: {response.usage.total_tokens}")
            self._call_stats["total_tokens_used"] += response.usage.total_tokens

        # Procesar respuesta
        result = {
            "provider": self.provider,
            "message": message.content,
            "tool_calls": [],
            "raw_response": {
                "finish_reason": response.choices[0].finish_reason,
                "model": response.model if hasattr(response, 'model') else self.model,
            }
        }

        if message.tool_calls:
            logger.debug(f"  ORCHESTRATOR [OpenAI]: {len(message.tool_calls)} tool call(s)")
            for tool_call in message.tool_calls:
                try:
                    parsed_args = json.loads(tool_call.function.arguments)
                    result["tool_calls"].append({
                        "id": tool_call.id,
                        "name": tool_call.function.name,
                        "arguments": parsed_args,
                    })
                    logger.debug(f"  ORCHESTRATOR [OpenAI]: Tool: {tool_call.function.name}({parsed_args})")
                except json.JSONDecodeError as je:
                    logger.error(f"  ORCHESTRATOR [OpenAI] ERROR: JSON invalid: {je}")
                    raise ValueError(f"Invalid JSON in tool call arguments: {tool_call.function.arguments}")
        else:
            logger.debug(f"  ORCHESTRATOR [OpenAI]: No tool calls.")

        return result

    def _call_anthropic(self, context: str, tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Llama a Anthropic con el contexto y herramientas.
        Implementa reintentos automáticos para timeouts y errores de red.

        Args:
            context: Contexto formateado
            tools: Definición de herramientas

        Returns:
            Respuesta de la IA
        """
        logger.debug("  ORCHESTRATOR [Anthropic]: Preparando llamada...")

        # Convertir herramientas al formato de Anthropic
        logger.debug("AI_ORCHESTRATOR [Anthropic]: Convirtiendo herramientas al formato Anthropic...")
        anthropic_tools = []
        for tool in tools:
            anthropic_tools.append({
                "name": tool["function"]["name"],
                "description": tool["function"]["description"],
                "input_schema": tool["function"]["parameters"],
            })
        logger.debug(f"AI_ORCHESTRATOR [Anthropic]: {len(anthropic_tools)} herramientas configuradas")
        
        logger.debug(f"  ORCHESTRATOR [Anthropic]: Modelo: {self.model} | System: {len(SYSTEM_PROMPT)} chars | Context: {len(context)} chars")

        # Reintentos configurables via Config
        max_retries = Config.AI_API_MAX_RETRIES
        retry_delay = Config.AI_API_RETRY_DELAY
        timeout = Config.AI_API_TIMEOUT

        last_error = None
        for attempt in range(1, max_retries + 2):  # +2 porque range excluye el último y queremos max_retries reintentos
            try:
                if attempt > 1:
                    logger.info(f"AI_ORCHESTRATOR [Anthropic]: Reintento {attempt - 1}/{max_retries}...")
                    time.sleep(retry_delay)

                logger.info(f"  ORCHESTRATOR [Anthropic]: Enviando request (intento {attempt}/{max_retries + 1}, timeout={timeout}s)...")

                # Usar timeout forzado a nivel de thread
                forced_timeout = timeout + 5.0

                def _make_request():
                    return self.client.messages.create(
                        model=self.model,
                        max_tokens=1024,
                        system=SYSTEM_PROMPT,
                        messages=[
                            {"role": "user", "content": context},
                        ],
                        tools=anthropic_tools,
                        timeout=timeout,
                    )

                message = self._call_with_forced_timeout(_make_request, forced_timeout, "Anthropic API")
                logger.info("  ORCHESTRATOR [Anthropic]: ✓ Response recibido")

                # Si llegamos aquí, la llamada fue exitosa
                break
            except Exception as e:
                last_error = e
                logger.warning(f"  ORCHESTRATOR [Anthropic] WARNING: {type(e).__name__}: {str(e)}")

                # Verificar si es un error recuperable
                is_retryable = self._is_retryable_error(e)
                if is_retryable:
                    if attempt < max_retries + 1:
                        logger.info(f"  ORCHESTRATOR [Anthropic]: Error recuperable. Reintentando...")
                        # El sleep se ejecuta al inicio del siguiente intento (cuando attempt > 1)
                        continue
                    else:
                        logger.error(f"  ORCHESTRATOR [Anthropic] ERROR: Se agotaron los reintentos ({max_retries})")
                else:
                    # Error no recuperable, fallar inmediatamente
                    logger.error(f"  ORCHESTRATOR [Anthropic] ERROR: Error no recuperable detectado.")
                    break

        # Si llegamos aquí y last_error no es None, todos los intentos fallaron
        if last_error is not None:
            logger.error(f"AI_ORCHESTRATOR [Anthropic] ERROR: Fallo en API call después de {max_retries + 1} intentos")
            logger.error(f"AI_ORCHESTRATOR [Anthropic] ERROR: {type(last_error).__name__}: {str(last_error)}")
            
            # Diagnóstico de errores comunes
            error_str = str(last_error).lower()
            if "authentication" in error_str or "api key" in error_str or "invalid x-api-key" in error_str:
                logger.error("AI_ORCHESTRATOR [Anthropic] DIAGNÓSTICO: Problema de autenticación. Verifica ANTHROPIC_API_KEY")
            elif "rate limit" in error_str:
                logger.error("AI_ORCHESTRATOR [Anthropic] DIAGNÓSTICO: Rate limit alcanzado. Espera antes de reintentar")
            elif "model" in error_str:
                logger.error(f"AI_ORCHESTRATOR [Anthropic] DIAGNÓSTICO: Problema con el modelo '{self.model}'")
            elif "timeout" in error_str or "connection" in error_str:
                logger.error("AI_ORCHESTRATOR [Anthropic] DIAGNÓSTICO: Problema de conexión/timeout")
            
            raise last_error

        # Log detalles de la respuesta
        logger.debug(f"AI_ORCHESTRATOR [Anthropic]: stop_reason: {message.stop_reason}")
        if hasattr(message, 'usage') and message.usage:
            logger.debug(f"AI_ORCHESTRATOR [Anthropic]: Tokens - input: {message.usage.input_tokens}, "
                        f"output: {message.usage.output_tokens}")
            self._call_stats["total_tokens_used"] += (message.usage.input_tokens + message.usage.output_tokens)

        # Procesar respuesta - extraer mensaje de texto
        text_message = None
        if message.content:
            for content_block in message.content:
                if hasattr(content_block, 'type') and content_block.type == 'text':
                    text_message = content_block.text
                    break
        
        result = {
            "provider": "anthropic",
            "message": text_message,
            "tool_calls": [],
            "raw_response": {
                "stop_reason": message.stop_reason,
                "model": message.model if hasattr(message, 'model') else self.model,
            }
        }

        # Anthropic usa stop_reason y content blocks para tool calls
        # Revisar si hay tool_use en el contenido
        if message.content:
            logger.debug(f"AI_ORCHESTRATOR [Anthropic]: Procesando {len(message.content)} content block(s)")
            for idx, content_block in enumerate(message.content):
                block_type = getattr(content_block, 'type', 'unknown')
                logger.debug(f"AI_ORCHESTRATOR [Anthropic]: Block {idx}: tipo={block_type}")
                
                if hasattr(content_block, 'type') and content_block.type == 'tool_use':
                    result["tool_calls"].append({
                        "id": content_block.id,
                        "name": content_block.name,
                        "arguments": content_block.input,
                    })
                    logger.debug(f"AI_ORCHESTRATOR [Anthropic]: Tool call: {content_block.name}({content_block.input})")

        if result["tool_calls"]:
            logger.debug(f"AI_ORCHESTRATOR [Anthropic]: {len(result['tool_calls'])} tool call(s) extraídas")
        else:
            logger.debug(f"AI_ORCHESTRATOR [Anthropic]: Sin tool calls. Mensaje: {text_message}")

        return result
    
    def decide_step_completion(
        self,
        context: StepContext,
        last_action: Dict[str, Any],
        last_result: str,
        current_ui: List[Dict[str, Any]],
        override_step_description: Optional[str] = None,
        check_type: str = "current"  # "current" o "next"
    ) -> Dict[str, Any]:
        """
        Consulta al LLM para determinar si el paso está completo basándose
        en el resultado de la última acción ejecutada o estado de UI.
        
        Args:
            context: Contexto del paso actual
            last_action: Última acción ejecutada (tool_call)
            last_result: Resultado de la última acción (string)
            current_ui: Elementos UI actuales
            override_step_description: Si se proporciona, se valida este texto en lugar del paso actual
            check_type: 'current' (paso activo) o 'next' (validación de cascada)
            
        Returns:
            {
                "step_completed": bool,
                "reason": str
            }
        """
        inspector_tag = f"[INSPECTOR:{check_type.upper()}]"
        logger.info(f"{inspector_tag}: Consultando completitud")
        
        self._call_stats["total_calls"] += 1
        call_number = self._call_stats["total_calls"]
        logger.info(f"{inspector_tag}: Llamada de completitud #{call_number}")
        
        # Construir contexto para completitud
        llm_context = self._build_completion_context(
            context=context,
            last_action=last_action,
            last_result=last_result,
            current_ui=current_ui,
            override_step_description=override_step_description
        )
        
        # Llamar al LLM según el proveedor (sin tools, solo texto)
        start_time = time.time()
        try:
            logger.info(f"{inspector_tag}: Llamando a {self.provider} ({self.model})...")
            
            if self.provider in ["openai", "deepseek"]:
                result = self._call_openai_completion(llm_context, check_type)
            else:  # anthropic
                result = self._call_anthropic_completion(llm_context, check_type)
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            self._call_stats["successful_calls"] += 1
            self._call_stats["total_time_ms"] += elapsed_ms
            
            logger.info(f"{inspector_tag}: ✓ Decisión recibida en {elapsed_ms}ms")
            
            # Parsear respuesta JSON
            parsed = self._parse_completion_response(result)
            logger.info(f"{inspector_tag}: completed={parsed.get('step_completed')} | reason={parsed.get('reason')}")
            
            return parsed
            
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            self._call_stats["failed_calls"] += 1
            logger.error(f"{inspector_tag}: Fallo en llamada de completitud #{call_number} después de {elapsed_ms}ms")
            logger.error(f"{inspector_tag}: {type(e).__name__}: {str(e)}")

            # Intentar fallback si está habilitado
            fallback_result = self._try_fallback_provider(
                call_type="completion",
                context=llm_context,
                primary_error=e,
            )
            if fallback_result is not None and "raw_response" in fallback_result:
                logger.info(f"{inspector_tag}: ✓ Fallback de completitud exitoso con '{fallback_result.get('fallback_provider', 'unknown')}'")
                parsed = self._parse_completion_response(fallback_result["raw_response"])
                return parsed

            # No hay fallback o todos fallaron - retornar valores por defecto
            logger.error(f"{inspector_tag}: Traceback:\n{traceback.format_exc()}")
            return {
                "step_completed": False,
                "reason": f"Error checking completion: {str(e)}"
            }

    def _build_completion_context(
        self,
        context: StepContext,
        last_action: Dict[str, Any],
        last_result: str,
        current_ui: List[Dict[str, Any]],
        override_step_description: Optional[str] = None
    ) -> str:
        """
        Construye contexto para consulta de completitud.
        Mantiene formato similar al historial actual.
        """
        parts: List[str] = []
        
        # Historial de ejecución (similar al actual)
        parts.append("### Historial de ejecución")
        if context.action_history:
            # Convertir action_history a TOON (ya incluye resultados en V2)
            try:
                history_toon = toon_encode(context.action_history, {"delimiter": "\t"})
                parts.append(history_toon)
            except Exception as e:
                logger.warning(
                    "[INSPECTOR]: No se pudo convertir action_history a TOON: %s", e
                )
                for action in context.action_history:
                    if isinstance(action, dict):
                        parts.append(f"  {action.get('index', '?')}. {action.get('action', 'N/A')} -> {action.get('result', 'N/A')}")
                    else:
                        parts.append(f"  - {action}")
        else:
            parts.append("  (Sin acciones previas)")
        parts.append("")
        
        # Última acción (V2)
        parts.append("### Última acción ejecutada")
        
        # Validar si hay información de la última acción
        action_name = last_action.get('name', 'N/A') if last_action else 'N/A'
        action_args = last_action.get('arguments', {}) if last_action else {}
        
        last_action_entry = {
            "action": f"{action_name}({action_args})",
            "result": last_result if last_result else "N/A",
        }
        try:
            last_action_toon = toon_encode([last_action_entry], {"delimiter": "\t"})
            parts.append(last_action_toon)
        except Exception as e:
            logger.warning("[INSPECTOR]: No se pudo convertir última acción a TOON: %s", e)
            parts.append(f"  Acción: {action_name}({action_args})")
            parts.append(f"  Resultado: {last_result}")
        parts.append("")
        
        # Paso a verificar (actual o override)
        target_step = override_step_description if override_step_description else context.current_step
        parts.append(f"## Objetivo a verificar: {target_step}")

        # Incluir next_step como contexto para INSPECTOR:CURRENT
        # Esto ayuda a inferir si el paso actual se completó cuando la acción
        # cambia la pantalla (ej: si el siguiente paso es "Verificar dashboard"
        # y ya estamos en dashboard, el paso actual de "hacer login" está completo)
        if not override_step_description and context.next_step:
            parts.append(f"### Próximo paso en el plan: {context.next_step}")
        parts.append("")

        # Elementos disponibles (TOON)
        parts.append("### Elementos disponibles en la pantalla")
        if current_ui:
            # Usar modo "inspector" para la consulta de completitud
            filtered_elements = self._filter_ui_elements_for_toon(current_ui, mode="inspector")
            try:
                elements_toon = toon_encode(filtered_elements, {"delimiter": "|"})
                parts.append(elements_toon)
            except Exception as e:
                logger.warning("[INSPECTOR]: No se pudo convertir elementos a TOON: %s", e)
                parts.append(f"  ({len(current_ui)} elementos disponibles)")
        else:
            parts.append("  (No hay elementos interactuables visibles)")
        parts.append("")
        
        # Instrucciones
        parts.append("## Determina:")
        parts.append("1. ¿El paso actual está completo? (basándote en el resultado de la acción)")
        parts.append("2. ¿El siguiente paso ya fue completado? (por ejemplo, si presionaste un botón y llegaste a la pantalla del siguiente paso)")
        
        context_str = "\n".join(parts)
        logger.info(f"[INSPECTOR]: Contexto generado: \n\n{context_str}")

        return context_str
    
    def _parse_completion_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parsea la respuesta del LLM para determinar si el paso está completo.
        Prioriza JSON.
        """
        # 1. Intentar parsear como JSON directo
        try:
            import json
            data = json.loads(response_text)
            return {
                "step_completed": data.get("step_completed", False),
                "reason": data.get("reason", "No reason provided")
            }
        except:
            pass

        # 2. Buscar bloque JSON con regex
        try:
            import re
            import json
            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return {
                    "step_completed": data.get("step_completed", False),
                    "reason": data.get("reason", "No reason provided")
                }
        except:
            pass

        # 3. Fallback a parseo de texto simple
        return self._parse_completion_response_fallback(response_text)
    
    def _parse_completion_response_fallback(self, response_text: str) -> Dict[str, Any]:
        """
        Fallback parser para respuestas que no están en formato TOON.
        Intenta extraer información del texto de forma conservadora.
        """
        response_lower = response_text.lower()
        
        # Solo marcar como completado si hay una confirmación explícita y positiva
        # Evitamos 'completar' si la IA está explicando por qué NO está completo
        step_completed = False
        if any(marker in response_lower for marker in ["step_completed: true", "step_completed|true", "true|", "|true"]):
            step_completed = True
        elif ("completado" in response_lower or "completo" in response_lower) and "no " not in response_lower:
             # Heurística simple: 'completo' sin un 'no' cerca
             step_completed = True
        
        return {
            "step_completed": step_completed,
            "reason": response_text[:200]
        }
    
    def _get_completion_system_prompt(self, check_type: str) -> str:
        """Retorna el prompt especializado según el tipo de verificación."""
        base_format = """
FORMATO DE ELEMENTOS (TOON):
Los atributos están optimizados para la VERIFICACIÓN:
- "id": ID del elemento
- "possible_element_type": Tipo de widget (input, button, etc.)
- "xpath": Ubicación técnica
- "text": CONTENIDO ACTUAL del campo (texto ingresado por el usuario). Si está presente, el campo FUE RELLENADO.
- "hint": PLACEHOLDER del campo (texto de ayuda). Si está presente SIN "text", el campo está VACÍO.
- "focused": "true" si tiene el foco actual
- "checked": "true" si está marcado
- "password": "true" si es campo de contraseña (el texto se muestra como asteriscos)

SEMÁNTICA CRÍTICA PARA INPUTS (possible_element_type="input"):
- Campo CON "text" → FUE RELLENADO (tiene contenido del usuario)
- Campo CON "hint" pero SIN "text" → ESTÁ VACÍO (solo muestra placeholder)
- Campo SIN "text" NI "hint" → ESTÁ VACÍO
- Para campos password="true", el "text" aparece como asteriscos (***) pero CONFIRMA que tiene contenido

RESPUESTA EN FORMATO JSON:
Responde EXCLUSIVAMENTE con un objeto JSON válido con la siguiente estructura:
{
  "step_completed": true,
  "reason": "Explicación breve citando evidencia visual o resultado de la acción"
}

- step_completed: boolean (true/false)
- reason: string (breve explicación)
"""

        if check_type == "current":
            return """Eres QAI (QA Agent V2).

ROL: INSPECTOR DE PASO ACTUAL
Tu misión es VERIFICAR si el paso activo se ha completado exitosamente.

CRITERIOS DE COMPLETITUD (PASO ACTUAL):
1. Acción Exitosa + Resultado Visual:
   - Si la acción (tool) reportó "Success" Y la UI cambió mostrando el resultado esperado (navegación, texto ingresado, etc.), el paso está COMPLETO.

2. Verificaciones (Asserts):
   - Si el paso es "Verificar X" o "Esperar Y" y el elemento ya es visible en la UI actual, el paso está COMPLETO.

3. Estado ya alcanzado (sin acción directa):
   - Si no hubo acción específica para este paso pero el estado ya existe en la UI, evalúa solo basándote en la UI actual.
   - Si el paso dice "Verificar que se ve pantalla X" y YA estamos en pantalla X, retorna TRUE.
   - Si el paso dice "Esperar a ver botón Y" y el botón Y YA es visible, retorna TRUE.

4. REGLA CRÍTICA PARA PASOS DE "INGRESAR/ESCRIBIR/LLENAR/TOCAR":
   - Si el paso requiere una ACCIÓN (ingresar texto, tocar botón) y NO se ejecutó una acción para este paso, retorna FALSE.
   - NUNCA marques como completo un paso de "Ingresar X en campo Y" sin verificar que ESE CAMPO ESPECÍFICO tiene "text".
   - Debes identificar EL CAMPO CORRECTO mencionado en el paso (ej: "confirmación de contraseña" ≠ "contraseña").
   - Si el campo destino NO tiene atributo "text" (o solo tiene "hint"), el paso NO está completo. Retorna FALSE.

5. AMBIGÜEDAD "CONFIRMAR":
   - Si el paso dice "Confirmar X" (ej: "Confirmar cierre de sesión"), esto suele implicar una ACCIÓN (tocar "Sí/Aceptar").
   - Si solo ves el diálogo abierto pero no has tocado la opción de confirmar en él, el paso NO está completo.

6. Análisis de Evidencia:
   - Usa el 'text', 'hint' y estructura de la UI para confirmar que lo que pide el paso ya ocurrió.
""" + base_format

        elif check_type == "next":
            return """Eres QAI (QA Agent V2).

ROL: INSPECTOR ADELANTADO (ANTICIPATOR)
Tu misión es VERIFICAR si el *siguiente paso* del plan se completó AUTOMÁTICAMENTE como efecto secundario de acciones previas, O si ya estaba completo desde el inicio.
NO se ha ejecutado ninguna acción específica para este paso aún. Solo estás mirando la UI resultante.

CRITERIOS DE COMPLETITUD (PASO SIGUIENTE):
1. Estado ya alcanzado:
   - Si el paso dice "Verificar que se ve pantalla X" y YA estamos en pantalla X, retorna TRUE.
   - Si el paso dice "Esperar a ver botón Y" y el botón Y YA es visible, retorna TRUE.

2. Navegación implícita:
   - Si una acción anterior ya nos llevó al destino de este paso, retorna TRUE.

3. REGLA CRÍTICA PARA PASOS DE "INGRESAR/ESCRIBIR/LLENAR":
   - NUNCA marques como completo un paso de "Ingresar X en campo Y" sin verificar que ESE CAMPO ESPECÍFICO tiene "text".
   - Debes identificar EL CAMPO CORRECTO mencionado en el paso (ej: "confirmación de contraseña" ≠ "contraseña").
   - Si el campo destino NO tiene atributo "text" (o solo tiene "hint"), el paso NO está completo. Retorna FALSE.
   - Que OTRO campo similar tenga "text" NO significa que ESTE paso esté completo.

4. IMPORTANTE:
   - Si el paso requiere una acción nueva ACTIVA (ej: "Ingresar texto", "Tocar botón"), entonces NO está completo. Retorna FALSE.
   - Solo pasos de verificación/espera suelen autocompletarse.
""" + base_format
        
        else:
            return "Eres un asistente QA."


    def _call_openai_completion(self, context: str, check_type: str = "current") -> str:
        """
        Llama a OpenAI para determinar completitud con prompt especializado.
        Implementa reintentos automáticos para timeouts y errores de red.
        """
        system_prompt = self._get_completion_system_prompt(check_type)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context},
        ]

        # Reintentos configurables via Config
        max_retries = Config.AI_API_MAX_RETRIES
        retry_delay = Config.AI_API_RETRY_DELAY
        timeout = Config.AI_API_TIMEOUT

        last_error = None
        for attempt in range(1, max_retries + 2):  # +2 porque range excluye el último y queremos max_retries reintentos
            try:
                if attempt > 1:
                    logger.info(f"AI_ORCHESTRATOR [OpenAI] Completitud: Reintento {attempt - 1}/{max_retries}...")
                    time.sleep(retry_delay)

                # Usar timeout forzado a nivel de thread para garantizar que NUNCA se quede colgado
                # Agrega 5s de margen al timeout configurado para el wrapper
                forced_timeout = timeout + 5.0

                def _make_completion_request():
                    return self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=0.2,
                        timeout=timeout,
                        response_format={"type": "json_object"}
                    )

                response = self._call_with_forced_timeout(_make_completion_request, forced_timeout, "OpenAI Completion")

                message = response.choices[0].message
                return message.content or "{}"

            except Exception as e:
                last_error = e
                logger.warning(f"AI_ORCHESTRATOR [OpenAI] Completitud WARNING: Intento {attempt}/{max_retries + 1} falló")
                logger.warning(f"AI_ORCHESTRATOR [OpenAI] Completitud WARNING: {type(e).__name__}: {str(e)}")

                # Verificar si es un error recuperable
                is_retryable = self._is_retryable_error(e)
                if is_retryable:
                    if attempt < max_retries + 1:
                        logger.info(f"AI_ORCHESTRATOR [OpenAI] Completitud: Error recuperable detectado (timeout/red/SSL). Reintentando en {retry_delay}s... (intento {attempt}/{max_retries})")
                        continue
                    else:
                        logger.error(f"AI_ORCHESTRATOR [OpenAI] Completitud ERROR: Se agotaron los reintentos ({max_retries}) para error recuperable")
                else:
                    # Error no recuperable, fallar inmediatamente
                    logger.error(f"AI_ORCHESTRATOR [OpenAI] Completitud ERROR: Error no recuperable detectado. No se reintentará.")
                    break

        # Si llegamos aquí, todos los intentos fallaron
        if last_error is not None:
            logger.error(f"AI_ORCHESTRATOR [OpenAI] Completitud ERROR: Fallo después de {max_retries + 1} intentos: {last_error}")
            raise last_error
        
        # No debería llegar aquí, pero por si acaso
        raise RuntimeError("Error desconocido en _call_openai_completion")
    
    def _call_anthropic_completion(self, context: str, check_type: str = "current") -> str:
        """
        Llama a Anthropic para determinar completitud con prompt especializado.
        Implementa reintentos automáticos para timeouts y errores de red.
        """
        system_prompt = self._get_completion_system_prompt(check_type)

        # Reintentos configurables via Config
        max_retries = Config.AI_API_MAX_RETRIES
        retry_delay = Config.AI_API_RETRY_DELAY
        timeout = Config.AI_API_TIMEOUT

        last_error = None
        for attempt in range(1, max_retries + 2):  # +2 porque range excluye el último y queremos max_retries reintentos
            try:
                if attempt > 1:
                    logger.info(f"AI_ORCHESTRATOR [Anthropic] Completitud: Reintento {attempt - 1}/{max_retries}...")
                    time.sleep(retry_delay)

                # Usar timeout forzado a nivel de thread
                forced_timeout = timeout + 5.0

                def _make_completion_request():
                    return self.client.messages.create(
                        model=self.model,
                        max_tokens=512,
                        system=system_prompt,
                        messages=[
                            {"role": "user", "content": context},
                        ],
                        timeout=timeout,
                    )

                message = self._call_with_forced_timeout(_make_completion_request, forced_timeout, "Anthropic Completion")

                # Extraer mensaje de texto
                text_message = None
                if message.content:
                    for content_block in message.content:
                        if hasattr(content_block, 'type') and content_block.type == 'text':
                            text_message = content_block.text
                            break

                return text_message or ""

            except Exception as e:
                last_error = e
                logger.warning(f"AI_ORCHESTRATOR [Anthropic] Completitud WARNING: Intento {attempt}/{max_retries + 1} falló")
                logger.warning(f"AI_ORCHESTRATOR [Anthropic] Completitud WARNING: {type(e).__name__}: {str(e)}")

                # Verificar si es un error recuperable
                is_retryable = self._is_retryable_error(e)
                if is_retryable:
                    if attempt < max_retries + 1:
                        logger.info(f"AI_ORCHESTRATOR [Anthropic] Completitud: Error recuperable detectado (timeout/red/SSL). Reintentando en {retry_delay}s... (intento {attempt}/{max_retries})")
                        continue
                    else:
                        logger.error(f"AI_ORCHESTRATOR [Anthropic] Completitud ERROR: Se agotaron los reintentos ({max_retries}) para error recuperable")
                else:
                    # Error no recuperable, fallar inmediatamente
                    logger.error(f"AI_ORCHESTRATOR [Anthropic] Completitud ERROR: Error no recuperable detectado. No se reintentará.")
                    break
        
        # Si llegamos aquí, todos los intentos fallaron
        if last_error is not None:
            logger.error(f"AI_ORCHESTRATOR [Anthropic] Completitud ERROR: Fallo después de {max_retries + 1} intentos: {last_error}")
            raise last_error
        
        # No debería llegar aquí, pero por si acaso
        raise RuntimeError("Error desconocido en _call_anthropic_completion")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        DEBUG: Retorna estadísticas de las llamadas al LLM.
        """
        stats = self._call_stats.copy()
        if stats["total_calls"] > 0:
            stats["success_rate"] = f"{(stats['successful_calls'] / stats['total_calls']) * 100:.1f}%"
            stats["avg_time_ms"] = stats["total_time_ms"] // stats["total_calls"]
        return stats

