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
from typing import List, Dict, Any, Optional
from openai import OpenAI
from anthropic import Anthropic

from toon_format import encode as toon_encode

from src.config import Config

# Configurar logging para este módulo
logger = logging.getLogger(__name__)

# =============================================================================
# SYSTEM PROMPT - Compartido entre OpenAI y Anthropic
# =============================================================================
SYSTEM_PROMPT = """Eres un Agente de QA Móvil autónomo. Tu objetivo es ejecutar pruebas en aplicaciones móviles Android.

FORMATO DE ELEMENTOS (TOON):
Los elementos se muestran en formato tabular TOON. Cada fila es un elemento con sus atributos.
- "id": número único (USAR ESTE en las herramientas)
- Los demás campos son atributos del elemento Android

Ejemplo TOON:
[2]{id	content-desc	class	xpath	clickable}:
  0	Botón login	android.widget.Button	//android.widget.Button[@content-desc="Botón login"]	true
  1	Campo email	android.widget.EditText	//android.widget.EditText[@content-desc="Campo email"]	true

ATRIBUTOS IMPORTANTES PARA IDENTIFICAR ELEMENTOS:
- "content-desc": Texto de accesibilidad (lo que describe el elemento)
- "text": Texto visible en el elemento
- "resource-id": ID del recurso Android
- "class": Tipo de elemento (Button, EditText, View, etc.)
- "hint": Placeholder en campos de texto

IMPORTANTE - USO DE IDs:
- USA el campo "id" del elemento en las herramientas
- Ejemplo: touch_element_by_id(element_id=0), fill_field_by_id(element_id=1, value="texto")
- NO confundas "id" con el atributo "resource-id" (son diferentes)

INSTRUCCIONES:
1. Busca el elemento correcto por sus atributos (content-desc, text, class)
2. Usa el "id" de ese elemento en la herramienta correspondiente
3. Ejecuta SOLO UNA acción por turno
4. Para campos de texto (class contiene "EditText"), usa fill_field_by_id
5. Para hacer click, usa touch_element_by_id
6. Si no encuentras un elemento, usa scroll
7. Para verificaciones usa assert_screen_contains

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

IMPORTANTE: Ejecuta SOLO la acción del paso ACTUAL. NO te adelantes a pasos futuros."""


class AIOrchestrator:
    """
    Orquestador de IA que analiza la UI parseada y decide qué acciones ejecutar.
    """

    def __init__(self):
        """Inicializa el orquestador con el proveedor de IA configurado."""
        logger.info("=" * 70)
        logger.info("AI_ORCHESTRATOR: Inicializando orquestador de IA")
        logger.info("=" * 70)
        
        self.provider = Config.DEFAULT_AI_PROVIDER
        logger.info(f"AI_ORCHESTRATOR: Proveedor seleccionado: {self.provider}")
        
        # Estadísticas de llamadas
        self._call_stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_tokens_used": 0,
            "total_time_ms": 0,
        }
        
        if self.provider == "openai":
            logger.debug("AI_ORCHESTRATOR: Configurando cliente OpenAI...")
            if not Config.OPENAI_API_KEY:
                logger.error("AI_ORCHESTRATOR ERROR: OPENAI_API_KEY no está configurada")
                raise ValueError("OPENAI_API_KEY no está configurada")
            
            # Verificar formato de API key (debe empezar con sk-)
            if not Config.OPENAI_API_KEY.startswith("sk-"):
                logger.warning("AI_ORCHESTRATOR WARNING: OPENAI_API_KEY no tiene el formato esperado (sk-...)")
            
            self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
            self.model = Config.OPENAI_MODEL
            logger.info(f"AI_ORCHESTRATOR: ✓ Cliente OpenAI configurado con modelo: {self.model}")
            
        elif self.provider == "anthropic":
            logger.debug("AI_ORCHESTRATOR: Configurando cliente Anthropic...")
            if not Config.ANTHROPIC_API_KEY:
                logger.error("AI_ORCHESTRATOR ERROR: ANTHROPIC_API_KEY no está configurada")
                raise ValueError("ANTHROPIC_API_KEY no está configurada")
            
            self.client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)
            self.model = Config.ANTHROPIC_MODEL
            logger.info(f"AI_ORCHESTRATOR: ✓ Cliente Anthropic configurado con modelo: {self.model}")
            
        elif self.provider == "deepseek":
            logger.debug("AI_ORCHESTRATOR: Configurando cliente DeepSeek...")
            if not Config.DEEPSEEK_API_KEY:
                logger.error("AI_ORCHESTRATOR ERROR: DEEPSEEK_API_KEY no está configurada")
                raise ValueError("DEEPSEEK_API_KEY no está configurada")
            
            # DeepSeek es compatible con OpenAI API, solo cambiamos el base_url
            self.client = OpenAI(
                api_key=Config.DEEPSEEK_API_KEY,
                base_url="https://api.deepseek.com"
            )
            self.model = Config.DEEPSEEK_MODEL
            logger.info(f"AI_ORCHESTRATOR: ✓ Cliente DeepSeek configurado con modelo: {self.model}")
            
        else:
            logger.error(f"AI_ORCHESTRATOR ERROR: Proveedor no soportado: {self.provider}")
            raise ValueError(f"Proveedor de IA no soportado: {self.provider}")

    def decide_next_action(
        self,
        ui_elements: List[Dict[str, Any]],
        current_step: str,
        action_history: List[str],
        objective: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analiza la UI parseada y decide qué acción ejecutar.

        Args:
            ui_elements: Lista de elementos JSON parseados por UIParser
            current_step: Paso actual a ejecutar
            action_history: Historial de acciones recientes (últimas 3-5)
            objective: Objetivo general del test (opcional)

        Returns:
            Diccionario con la decisión de la IA (tool_call o mensaje)
        """
        logger.info("=" * 70)
        logger.info("AI_ORCHESTRATOR: Solicitando decisión de acción")
        logger.info("=" * 70)
        
        self._call_stats["total_calls"] += 1
        call_number = self._call_stats["total_calls"]
        logger.info(f"AI_ORCHESTRATOR: Llamada #{call_number}")
        
        # Log inputs
        logger.debug(f"AI_ORCHESTRATOR: Objetivo: '{objective or 'No definido'}'")
        logger.debug(f"AI_ORCHESTRATOR: Paso actual: '{current_step}'")
        logger.debug(f"AI_ORCHESTRATOR: Elementos UI disponibles: {len(ui_elements)}")
        logger.debug(f"AI_ORCHESTRATOR: Historial de acciones: {len(action_history)} acciones")
        
        if not ui_elements:
            logger.warning("AI_ORCHESTRATOR WARNING: No hay elementos UI para analizar")
        
        # Preparar contexto para el LLM
        logger.debug("AI_ORCHESTRATOR: Construyendo contexto para el LLM...")
        context = self._build_context(ui_elements, current_step, action_history, objective)
        
        # Log del contexto completo (para debug profundo)
        logger.debug("AI_ORCHESTRATOR: Contexto generado:")
        for line in context.split('\n'):
            logger.debug(f"  {line}")

        # Definir herramientas disponibles
        tools = self._get_tools_definition()
        logger.debug(f"AI_ORCHESTRATOR: Herramientas disponibles: {[t['function']['name'] for t in tools]}")

        # Llamar al LLM según el proveedor
        start_time = time.time()
        try:
            if self.provider == "openai":
                logger.info(f"AI_ORCHESTRATOR: Llamando a OpenAI ({self.model})...")
                result = self._call_openai(context, tools)
            elif self.provider == "deepseek":
                logger.info(f"AI_ORCHESTRATOR: Llamando a DeepSeek ({self.model})...")
                result = self._call_openai(context, tools)  # DeepSeek usa la misma API que OpenAI
            else:  # anthropic
                logger.info(f"AI_ORCHESTRATOR: Llamando a Anthropic ({self.model})...")
                result = self._call_anthropic(context, tools)
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            self._call_stats["successful_calls"] += 1
            self._call_stats["total_time_ms"] += elapsed_ms
            
            logger.info(f"AI_ORCHESTRATOR: ✓ Respuesta recibida en {elapsed_ms}ms")
            
            # Log de la decisión
            if result.get("tool_calls"):
                for tc in result["tool_calls"]:
                    logger.info(f"AI_ORCHESTRATOR: Decisión -> {tc['name']}({tc['arguments']})")
            else:
                logger.info(f"AI_ORCHESTRATOR: Decisión -> No tool call. Mensaje: {result.get('message', 'N/A')}")
            
            return result
            
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            self._call_stats["failed_calls"] += 1
            logger.error(f"AI_ORCHESTRATOR ERROR: Fallo en llamada #{call_number} después de {elapsed_ms}ms")
            logger.error(f"AI_ORCHESTRATOR ERROR: {type(e).__name__}: {str(e)}")
            logger.error(f"AI_ORCHESTRATOR ERROR: Traceback:\n{traceback.format_exc()}")
            raise

    def _build_context(
        self,
        ui_elements: List[Dict[str, Any]],
        current_step: str,
        action_history: List[str],
        objective: Optional[str],
    ) -> str:
        """
        Construye el contexto para el prompt del LLM usando formato TOON.
        
        TOON (Token-Oriented Object Notation) reduce el consumo de tokens
        en un 30-60% comparado con JSON para arrays uniformes de objetos.
        
        Los elementos se mantienen en su estructura anidada {id, attrs: [{name, value}]}
        y se convierten directamente a TOON sin modificar su estructura.

        Args:
            ui_elements: Lista de elementos disponibles (UIElement con estructura {id, attrs})
            current_step: Paso actual
            action_history: Historial de acciones
            objective: Objetivo general

        Returns:
            String con el contexto formateado en TOON
        """
        context_parts = []

        # Objetivo general
        if objective:
            context_parts.append(f"Objetivo general: {objective}\n")

        # Paso actual
        context_parts.append(f"Paso actual a ejecutar: {current_step}\n")

        # Historial reciente
        if action_history:
            context_parts.append("Historial de acciones recientes:")
            for i, action in enumerate(action_history[-5:], 1):  # Últimas 5 acciones
                context_parts.append(f"  {i}. {action}")
            context_parts.append("")

        # Elementos disponibles en la pantalla (formato TOON)
        context_parts.append("Elementos disponibles en la pantalla (formato TOON):")
        if not ui_elements:
            context_parts.append("  (No hay elementos interactuables visibles)")
        else:
            # Convertir a TOON manteniendo la estructura anidada {id, attrs: [{name, value}]}
            toon_options = {
                "delimiter": "|",
            }
            toon_elements = toon_encode(ui_elements, toon_options)
            context_parts.append(toon_elements)
            
            logger.debug(f"AI_ORCHESTRATOR: Elementos convertidos a TOON ({len(toon_elements)} chars)")

        return "\n".join(context_parts)

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
                    "name": "scroll",
                    "description": "Hace scroll en la pantalla para ver más contenido. Útil cuando no encuentras el elemento que buscas.",
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
        ]

    def _call_openai(self, context: str, tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Llama a OpenAI con el contexto y herramientas.

        Args:
            context: Contexto formateado
            tools: Definición de herramientas

        Returns:
            Respuesta de la IA
        """
        logger.debug("AI_ORCHESTRATOR [OpenAI]: Preparando llamada a API...")

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": context},
        ]
        
        logger.debug(f"AI_ORCHESTRATOR [OpenAI]: Modelo: {self.model}")
        logger.debug(f"AI_ORCHESTRATOR [OpenAI]: Longitud del system prompt: {len(SYSTEM_PROMPT)} chars")
        logger.debug(f"AI_ORCHESTRATOR [OpenAI]: Longitud del contexto: {len(context)} chars")

        try:
            logger.debug("AI_ORCHESTRATOR [OpenAI]: Enviando request...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.3,  # Baja temperatura para decisiones más determinísticas
                store=True,  # Habilita almacenamiento en OpenAI Platform (logs/traces)
            )
            logger.debug("AI_ORCHESTRATOR [OpenAI]: ✓ Response recibido")
            
        except Exception as e:
            logger.error(f"AI_ORCHESTRATOR [OpenAI] ERROR: Fallo en API call")
            logger.error(f"AI_ORCHESTRATOR [OpenAI] ERROR: {type(e).__name__}: {str(e)}")
            
            # Diagnóstico de errores comunes
            error_str = str(e).lower()
            if "authentication" in error_str or "api key" in error_str:
                logger.error("AI_ORCHESTRATOR [OpenAI] DIAGNÓSTICO: Problema de autenticación. Verifica OPENAI_API_KEY")
            elif "rate limit" in error_str:
                logger.error("AI_ORCHESTRATOR [OpenAI] DIAGNÓSTICO: Rate limit alcanzado. Espera antes de reintentar")
            elif "model" in error_str:
                logger.error(f"AI_ORCHESTRATOR [OpenAI] DIAGNÓSTICO: Problema con el modelo '{self.model}'")
            elif "timeout" in error_str or "connection" in error_str:
                logger.error("AI_ORCHESTRATOR [OpenAI] DIAGNÓSTICO: Problema de conexión/timeout")
            
            raise

        message = response.choices[0].message
        
        # Log detalles de la respuesta
        logger.debug(f"AI_ORCHESTRATOR [OpenAI]: finish_reason: {response.choices[0].finish_reason}")
        if hasattr(response, 'usage') and response.usage:
            logger.debug(f"AI_ORCHESTRATOR [OpenAI]: Tokens - prompt: {response.usage.prompt_tokens}, "
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
            logger.debug(f"AI_ORCHESTRATOR [OpenAI]: {len(message.tool_calls)} tool call(s) recibidas")
            for tool_call in message.tool_calls:
                try:
                    parsed_args = json.loads(tool_call.function.arguments)
                    result["tool_calls"].append({
                        "id": tool_call.id,
                        "name": tool_call.function.name,
                        "arguments": parsed_args,
                    })
                    logger.debug(f"AI_ORCHESTRATOR [OpenAI]: Tool call: {tool_call.function.name}({parsed_args})")
                except json.JSONDecodeError as je:
                    logger.error(f"AI_ORCHESTRATOR [OpenAI] ERROR: No se pudo parsear arguments JSON")
                    logger.error(f"AI_ORCHESTRATOR [OpenAI] ERROR: Raw arguments: {tool_call.function.arguments}")
                    logger.error(f"AI_ORCHESTRATOR [OpenAI] ERROR: JSONDecodeError: {je}")
                    raise ValueError(f"Invalid JSON in tool call arguments: {tool_call.function.arguments}")
        else:
            logger.debug(f"AI_ORCHESTRATOR [OpenAI]: Sin tool calls. Mensaje: {message.content}")

        return result

    def _call_anthropic(self, context: str, tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Llama a Anthropic con el contexto y herramientas.

        Args:
            context: Contexto formateado
            tools: Definición de herramientas

        Returns:
            Respuesta de la IA
        """
        logger.debug("AI_ORCHESTRATOR [Anthropic]: Preparando llamada a API...")

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
        
        logger.debug(f"AI_ORCHESTRATOR [Anthropic]: Modelo: {self.model}")
        logger.debug(f"AI_ORCHESTRATOR [Anthropic]: Longitud del system prompt: {len(SYSTEM_PROMPT)} chars")
        logger.debug(f"AI_ORCHESTRATOR [Anthropic]: Longitud del contexto: {len(context)} chars")

        try:
            logger.debug("AI_ORCHESTRATOR [Anthropic]: Enviando request...")
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": context},
                ],
                tools=anthropic_tools,
            )
            logger.debug("AI_ORCHESTRATOR [Anthropic]: ✓ Response recibido")
            
        except Exception as e:
            logger.error(f"AI_ORCHESTRATOR [Anthropic] ERROR: Fallo en API call")
            logger.error(f"AI_ORCHESTRATOR [Anthropic] ERROR: {type(e).__name__}: {str(e)}")
            
            # Diagnóstico de errores comunes
            error_str = str(e).lower()
            if "authentication" in error_str or "api key" in error_str or "invalid x-api-key" in error_str:
                logger.error("AI_ORCHESTRATOR [Anthropic] DIAGNÓSTICO: Problema de autenticación. Verifica ANTHROPIC_API_KEY")
            elif "rate limit" in error_str:
                logger.error("AI_ORCHESTRATOR [Anthropic] DIAGNÓSTICO: Rate limit alcanzado. Espera antes de reintentar")
            elif "model" in error_str:
                logger.error(f"AI_ORCHESTRATOR [Anthropic] DIAGNÓSTICO: Problema con el modelo '{self.model}'")
            elif "timeout" in error_str or "connection" in error_str:
                logger.error("AI_ORCHESTRATOR [Anthropic] DIAGNÓSTICO: Problema de conexión/timeout")
            
            raise

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
    
    def get_stats(self) -> Dict[str, Any]:
        """
        DEBUG: Retorna estadísticas de las llamadas al LLM.
        """
        stats = self._call_stats.copy()
        if stats["total_calls"] > 0:
            stats["success_rate"] = f"{(stats['successful_calls'] / stats['total_calls']) * 100:.1f}%"
            stats["avg_time_ms"] = stats["total_time_ms"] // stats["total_calls"]
        return stats

