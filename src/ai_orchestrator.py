"""
AI Orchestrator - Orquesta las decisiones de IA para ejecutar acciones en la app móvil.
Soporta OpenAI y Anthropic.
"""

import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
from anthropic import Anthropic

from src.config import Config


class AIOrchestrator:
    """
    Orquestador de IA que analiza la UI parseada y decide qué acciones ejecutar.
    """

    def __init__(self):
        """Inicializa el orquestador con el proveedor de IA configurado."""
        self.provider = Config.DEFAULT_AI_PROVIDER
        
        if self.provider == "openai":
            if not Config.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY no está configurada")
            self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
            self.model = Config.OPENAI_MODEL
        elif self.provider == "anthropic":
            if not Config.ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY no está configurada")
            self.client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)
            self.model = Config.ANTHROPIC_MODEL
        else:
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
        # Preparar contexto para el LLM
        context = self._build_context(ui_elements, current_step, action_history, objective)

        # Definir herramientas disponibles
        tools = self._get_tools_definition()

        # Llamar al LLM según el proveedor
        if self.provider == "openai":
            return self._call_openai(context, tools)
        else:  # anthropic
            return self._call_anthropic(context, tools)

    def _build_context(
        self,
        ui_elements: List[Dict[str, Any]],
        current_step: str,
        action_history: List[str],
        objective: Optional[str],
    ) -> str:
        """
        Construye el contexto para el prompt del LLM.

        Args:
            ui_elements: Lista de elementos disponibles
            current_step: Paso actual
            action_history: Historial de acciones
            objective: Objetivo general

        Returns:
            String con el contexto formateado
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

        # Elementos disponibles en la pantalla
        context_parts.append("Elementos disponibles en la pantalla:")
        if not ui_elements:
            context_parts.append("  (No hay elementos interactuables visibles)")
        else:
            for element in ui_elements:
                element_str = f"  ID {element['id']}: {element['role']} - '{element['label']}'"
                if element.get('checked') is not None:
                    element_str += f" (checked: {element['checked']})"
                context_parts.append(element_str)

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
        system_prompt = """Eres un Agente de QA Móvil autónomo. Tu objetivo es ejecutar pruebas en aplicaciones móviles Android.

Instrucciones:
1. Analiza los elementos disponibles en la pantalla
2. Si ves popups o diálogos, ciérralos primero antes de continuar
3. Selecciona el elemento correcto del listado usando su ID
4. Usa las herramientas proporcionadas para interactuar con la app
5. Si no encuentras un elemento, intenta hacer scroll
6. Para validaciones, usa assert_screen_contains

Sé preciso y eficiente. Solo ejecuta la acción necesaria para completar el paso actual."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context},
        ]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.3,  # Baja temperatura para decisiones más determinísticas
        )

        message = response.choices[0].message

        # Procesar respuesta
        result = {
            "provider": "openai",
            "message": message.content,
            "tool_calls": [],
        }

        if message.tool_calls:
            for tool_call in message.tool_calls:
                result["tool_calls"].append({
                    "id": tool_call.id,
                    "name": tool_call.function.name,
                    "arguments": json.loads(tool_call.function.arguments),
                })

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
        system_prompt = """Eres un Agente de QA Móvil autónomo. Tu objetivo es ejecutar pruebas en aplicaciones móviles Android.

Instrucciones:
1. Analiza los elementos disponibles en la pantalla
2. Si ves popups o diálogos, ciérralos primero antes de continuar
3. Selecciona el elemento correcto del listado usando su ID
4. Usa las herramientas proporcionadas para interactuar con la app
5. Si no encuentras un elemento, intenta hacer scroll
6. Para validaciones, usa assert_screen_contains

Sé preciso y eficiente. Solo ejecuta la acción necesaria para completar el paso actual."""

        # Convertir herramientas al formato de Anthropic
        anthropic_tools = []
        for tool in tools:
            anthropic_tools.append({
                "name": tool["function"]["name"],
                "description": tool["function"]["description"],
                "input_schema": tool["function"]["parameters"],
            })

        message = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {"role": "user", "content": context},
            ],
            tools=anthropic_tools,
        )

        # Procesar respuesta
        result = {
            "provider": "anthropic",
            "message": message.content[0].text if message.content else None,
            "tool_calls": [],
        }

        # Anthropic usa stop_reason y content blocks para tool calls
        # Revisar si hay tool_use en el contenido
        if message.content:
            for content_block in message.content:
                if hasattr(content_block, 'type') and content_block.type == 'tool_use':
                    result["tool_calls"].append({
                        "id": content_block.id,
                        "name": content_block.name,
                        "arguments": content_block.input,
                    })

        return result

