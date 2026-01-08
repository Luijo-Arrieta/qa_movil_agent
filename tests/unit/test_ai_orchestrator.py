"""
Tests unitarios para AIOrchestrator (ai_orchestrator.py).
Usa mocks para los clientes de OpenAI y Anthropic.
"""

import json
import logging
import pytest
from unittest.mock import Mock, MagicMock, patch

logger = logging.getLogger(__name__)


class TestAIOrchestratorInit:
    """Tests para la inicialización de AIOrchestrator."""

    @patch('src.ai_orchestrator.Config')
    @patch('src.ai_orchestrator.OpenAI')
    def test_init_openai_success(self, mock_openai_class, mock_config):
        """Test: Inicialización exitosa con OpenAI."""
        mock_config.DEFAULT_AI_PROVIDER = "openai"
        mock_config.OPENAI_API_KEY = "sk-test-key-123"
        mock_config.OPENAI_MODEL = "gpt-4o"

        from src.ai_orchestrator import AIOrchestrator
        orchestrator = AIOrchestrator()

        assert orchestrator.provider == "openai"
        assert orchestrator.model == "gpt-4o"
        mock_openai_class.assert_called_once_with(api_key="sk-test-key-123")

    @patch('src.ai_orchestrator.Config')
    @patch('src.ai_orchestrator.Anthropic')
    def test_init_anthropic_success(self, mock_anthropic_class, mock_config):
        """Test: Inicialización exitosa con Anthropic."""
        mock_config.DEFAULT_AI_PROVIDER = "anthropic"
        mock_config.ANTHROPIC_API_KEY = "sk-ant-test-key"
        mock_config.ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"

        from src.ai_orchestrator import AIOrchestrator
        orchestrator = AIOrchestrator()

        assert orchestrator.provider == "anthropic"
        assert orchestrator.model == "claude-3-5-sonnet-20241022"
        mock_anthropic_class.assert_called_once_with(api_key="sk-ant-test-key")

    @patch('src.ai_orchestrator.Config')
    def test_init_missing_openai_key(self, mock_config):
        """Test: Error cuando falta OPENAI_API_KEY."""
        mock_config.DEFAULT_AI_PROVIDER = "openai"
        mock_config.OPENAI_API_KEY = None

        from src.ai_orchestrator import AIOrchestrator
        with pytest.raises(ValueError) as exc_info:
            AIOrchestrator()
        assert "OPENAI_API_KEY" in str(exc_info.value)

    @patch('src.ai_orchestrator.Config')
    def test_init_missing_anthropic_key(self, mock_config):
        """Test: Error cuando falta ANTHROPIC_API_KEY."""
        mock_config.DEFAULT_AI_PROVIDER = "anthropic"
        mock_config.ANTHROPIC_API_KEY = None

        from src.ai_orchestrator import AIOrchestrator
        with pytest.raises(ValueError) as exc_info:
            AIOrchestrator()
        assert "ANTHROPIC_API_KEY" in str(exc_info.value)

    @patch('src.ai_orchestrator.Config')
    def test_init_invalid_provider(self, mock_config):
        """Test: Error con proveedor no soportado."""
        mock_config.DEFAULT_AI_PROVIDER = "invalid_provider"

        from src.ai_orchestrator import AIOrchestrator
        with pytest.raises(ValueError) as exc_info:
            AIOrchestrator()
        assert "no soportado" in str(exc_info.value)


class TestBuildContext:
    """Tests para _build_context()."""

    @patch('src.ai_orchestrator.Config')
    @patch('src.ai_orchestrator.OpenAI')
    def test_build_context_with_all_params(self, mock_openai, mock_config):
        """Test: Construir contexto con todos los parámetros."""
        mock_config.DEFAULT_AI_PROVIDER = "openai"
        mock_config.OPENAI_API_KEY = "sk-test"
        mock_config.OPENAI_MODEL = "gpt-4o"

        from src.ai_orchestrator import AIOrchestrator
        orchestrator = AIOrchestrator()

        ui_elements = [
            {"id": 0, "role": "input", "label": "Email", "checked": None},
            {"id": 1, "role": "button", "label": "Login", "checked": None},
        ]
        context = orchestrator._build_context(
            ui_elements=ui_elements,
            current_step="Ingresar email",
            action_history=["Acción 1", "Acción 2"],
            objective="Probar login",
        )

        assert "Objetivo general: Probar login" in context
        assert "Paso actual a ejecutar: Ingresar email" in context
        assert "Historial de acciones recientes:" in context
        assert "Acción 1" in context
        assert "Elementos disponibles" in context
        # Verificar que hay contenido TOON (usa tabs como delimitador)
        assert "id" in context.lower()

    @patch('src.ai_orchestrator.Config')
    @patch('src.ai_orchestrator.OpenAI')
    def test_build_context_empty_elements(self, mock_openai, mock_config):
        """Test: Contexto con lista vacía de elementos."""
        mock_config.DEFAULT_AI_PROVIDER = "openai"
        mock_config.OPENAI_API_KEY = "sk-test"
        mock_config.OPENAI_MODEL = "gpt-4o"

        from src.ai_orchestrator import AIOrchestrator
        orchestrator = AIOrchestrator()

        context = orchestrator._build_context(
            ui_elements=[],
            current_step="Buscar botón",
            action_history=[],
            objective=None,
        )

        assert "No hay elementos interactuables" in context

    @patch('src.ai_orchestrator.Config')
    @patch('src.ai_orchestrator.OpenAI')
    def test_build_context_no_objective(self, mock_openai, mock_config):
        """Test: Contexto sin objetivo."""
        mock_config.DEFAULT_AI_PROVIDER = "openai"
        mock_config.OPENAI_API_KEY = "sk-test"
        mock_config.OPENAI_MODEL = "gpt-4o"

        from src.ai_orchestrator import AIOrchestrator
        orchestrator = AIOrchestrator()

        context = orchestrator._build_context(
            ui_elements=[{"id": 0, "role": "button", "label": "OK", "checked": None}],
            current_step="Click OK",
            action_history=[],
            objective=None,
        )

        assert "Objetivo general" not in context


class TestGetToolsDefinition:
    """Tests para _get_tools_definition()."""

    @patch('src.ai_orchestrator.Config')
    @patch('src.ai_orchestrator.OpenAI')
    def test_tools_definition_structure(self, mock_openai, mock_config):
        """Test: Estructura de definición de herramientas."""
        mock_config.DEFAULT_AI_PROVIDER = "openai"
        mock_config.OPENAI_API_KEY = "sk-test"
        mock_config.OPENAI_MODEL = "gpt-4o"

        from src.ai_orchestrator import AIOrchestrator
        orchestrator = AIOrchestrator()

        tools = orchestrator._get_tools_definition()

        assert isinstance(tools, list)
        assert len(tools) > 0

        # Verificar herramientas básicas
        tool_names = [t["function"]["name"] for t in tools]
        assert "touch_element_by_id" in tool_names
        assert "fill_field_by_id" in tool_names
        assert "scroll" in tool_names
        assert "go_back" in tool_names
        assert "assert_screen_contains" in tool_names

        # Verificar herramientas multi-app
        assert "activate_app" in tool_names
        assert "terminate_app" in tool_names
        assert "switch_to_app" in tool_names
        assert "switch_to_app_keep_background" in tool_names

    @patch('src.ai_orchestrator.Config')
    @patch('src.ai_orchestrator.OpenAI')
    def test_tool_has_required_fields(self, mock_openai, mock_config):
        """Test: Cada herramienta tiene campos requeridos."""
        mock_config.DEFAULT_AI_PROVIDER = "openai"
        mock_config.OPENAI_API_KEY = "sk-test"
        mock_config.OPENAI_MODEL = "gpt-4o"

        from src.ai_orchestrator import AIOrchestrator
        orchestrator = AIOrchestrator()

        tools = orchestrator._get_tools_definition()

        for tool in tools:
            assert "type" in tool
            assert tool["type"] == "function"
            assert "function" in tool
            assert "name" in tool["function"]
            assert "description" in tool["function"]
            assert "parameters" in tool["function"]


class TestCallOpenAI:
    """Tests para _call_openai()."""

    @patch('src.ai_orchestrator.Config')
    @patch('src.ai_orchestrator.OpenAI')
    def test_call_openai_with_tool_call(self, mock_openai_class, mock_config):
        """Test: Llamada a OpenAI que retorna tool call."""
        mock_config.DEFAULT_AI_PROVIDER = "openai"
        mock_config.OPENAI_API_KEY = "sk-test"
        mock_config.OPENAI_MODEL = "gpt-4o"

        # Mock de la respuesta de OpenAI
        mock_tool_call = Mock()
        mock_tool_call.id = "call_123"
        mock_tool_call.function.name = "touch_element_by_id"
        mock_tool_call.function.arguments = '{"element_id": 0}'

        mock_message = Mock()
        mock_message.content = None
        mock_message.tool_calls = [mock_tool_call]

        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "tool_calls"

        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.model = "gpt-4o"
        mock_response.usage = Mock(prompt_tokens=100, completion_tokens=50, total_tokens=150)

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        from src.ai_orchestrator import AIOrchestrator
        orchestrator = AIOrchestrator()

        result = orchestrator._call_openai("test context", [])

        assert result["provider"] == "openai"
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["name"] == "touch_element_by_id"
        assert result["tool_calls"][0]["arguments"] == {"element_id": 0}

    @patch('src.ai_orchestrator.Config')
    @patch('src.ai_orchestrator.OpenAI')
    def test_call_openai_no_tool_call(self, mock_openai_class, mock_config):
        """Test: Llamada a OpenAI que retorna mensaje sin tool call."""
        mock_config.DEFAULT_AI_PROVIDER = "openai"
        mock_config.OPENAI_API_KEY = "sk-test"
        mock_config.OPENAI_MODEL = "gpt-4o"

        mock_message = Mock()
        mock_message.content = "El paso está completado"
        mock_message.tool_calls = None

        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"

        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.model = "gpt-4o"
        mock_response.usage = Mock(prompt_tokens=100, completion_tokens=50, total_tokens=150)

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        from src.ai_orchestrator import AIOrchestrator
        orchestrator = AIOrchestrator()

        result = orchestrator._call_openai("test context", [])

        assert result["provider"] == "openai"
        assert len(result["tool_calls"]) == 0
        assert result["message"] == "El paso está completado"

    @patch('src.ai_orchestrator.Config')
    @patch('src.ai_orchestrator.OpenAI')
    def test_call_openai_api_error(self, mock_openai_class, mock_config):
        """Test: Error en API de OpenAI."""
        mock_config.DEFAULT_AI_PROVIDER = "openai"
        mock_config.OPENAI_API_KEY = "sk-test"
        mock_config.OPENAI_MODEL = "gpt-4o"

        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client

        from src.ai_orchestrator import AIOrchestrator
        orchestrator = AIOrchestrator()

        with pytest.raises(Exception) as exc_info:
            orchestrator._call_openai("test context", [])
        assert "API Error" in str(exc_info.value)


class TestCallAnthropic:
    """Tests para _call_anthropic()."""

    @patch('src.ai_orchestrator.Config')
    @patch('src.ai_orchestrator.Anthropic')
    def test_call_anthropic_with_tool_call(self, mock_anthropic_class, mock_config):
        """Test: Llamada a Anthropic que retorna tool use."""
        mock_config.DEFAULT_AI_PROVIDER = "anthropic"
        mock_config.ANTHROPIC_API_KEY = "sk-ant-test"
        mock_config.ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"

        # Mock de tool_use content block
        mock_tool_use = Mock()
        mock_tool_use.type = "tool_use"
        mock_tool_use.id = "toolu_123"
        mock_tool_use.name = "fill_field_by_id"
        mock_tool_use.input = {"element_id": 1, "value": "test@email.com"}

        mock_message = Mock()
        mock_message.content = [mock_tool_use]
        mock_message.stop_reason = "tool_use"
        mock_message.model = "claude-3-5-sonnet-20241022"
        mock_message.usage = Mock(input_tokens=100, output_tokens=50)

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_message
        mock_anthropic_class.return_value = mock_client

        from src.ai_orchestrator import AIOrchestrator
        orchestrator = AIOrchestrator()

        result = orchestrator._call_anthropic("test context", [])

        assert result["provider"] == "anthropic"
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["name"] == "fill_field_by_id"
        assert result["tool_calls"][0]["arguments"]["element_id"] == 1

    @patch('src.ai_orchestrator.Config')
    @patch('src.ai_orchestrator.Anthropic')
    def test_call_anthropic_text_response(self, mock_anthropic_class, mock_config):
        """Test: Llamada a Anthropic que retorna texto."""
        mock_config.DEFAULT_AI_PROVIDER = "anthropic"
        mock_config.ANTHROPIC_API_KEY = "sk-ant-test"
        mock_config.ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"

        mock_text_block = Mock()
        mock_text_block.type = "text"
        mock_text_block.text = "Paso completado exitosamente"

        mock_message = Mock()
        mock_message.content = [mock_text_block]
        mock_message.stop_reason = "end_turn"
        mock_message.model = "claude-3-5-sonnet-20241022"
        mock_message.usage = Mock(input_tokens=100, output_tokens=50)

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_message
        mock_anthropic_class.return_value = mock_client

        from src.ai_orchestrator import AIOrchestrator
        orchestrator = AIOrchestrator()

        result = orchestrator._call_anthropic("test context", [])

        assert result["provider"] == "anthropic"
        assert len(result["tool_calls"]) == 0
        assert result["message"] == "Paso completado exitosamente"

    @patch('src.ai_orchestrator.Config')
    @patch('src.ai_orchestrator.Anthropic')
    def test_call_anthropic_api_error(self, mock_anthropic_class, mock_config):
        """Test: Error en API de Anthropic."""
        mock_config.DEFAULT_AI_PROVIDER = "anthropic"
        mock_config.ANTHROPIC_API_KEY = "sk-ant-test"
        mock_config.ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"

        mock_client = Mock()
        mock_client.messages.create.side_effect = Exception("Anthropic API Error")
        mock_anthropic_class.return_value = mock_client

        from src.ai_orchestrator import AIOrchestrator
        orchestrator = AIOrchestrator()

        with pytest.raises(Exception) as exc_info:
            orchestrator._call_anthropic("test context", [])
        assert "Anthropic API Error" in str(exc_info.value)


class TestDecideNextAction:
    """Tests para decide_next_action()."""

    @patch('src.ai_orchestrator.Config')
    @patch('src.ai_orchestrator.OpenAI')
    def test_decide_action_calls_openai(self, mock_openai_class, mock_config):
        """Test: decide_next_action llama a OpenAI correctamente."""
        mock_config.DEFAULT_AI_PROVIDER = "openai"
        mock_config.OPENAI_API_KEY = "sk-test"
        mock_config.OPENAI_MODEL = "gpt-4o"

        # Mock respuesta
        mock_tool_call = Mock()
        mock_tool_call.id = "call_123"
        mock_tool_call.function.name = "scroll"
        mock_tool_call.function.arguments = '{"direction": "down"}'

        mock_message = Mock()
        mock_message.content = None
        mock_message.tool_calls = [mock_tool_call]

        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "tool_calls"

        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.model = "gpt-4o"
        mock_response.usage = Mock(prompt_tokens=100, completion_tokens=50, total_tokens=150)

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        from src.ai_orchestrator import AIOrchestrator
        orchestrator = AIOrchestrator()

        ui_elements = [{"id": 0, "role": "button", "label": "Login", "checked": None}]
        result = orchestrator.decide_next_action(
            ui_elements=ui_elements,
            current_step="Hacer scroll",
            action_history=[],
            objective="Probar scroll",
        )

        assert result["tool_calls"][0]["name"] == "scroll"
        mock_client.chat.completions.create.assert_called_once()

    @patch('src.ai_orchestrator.Config')
    @patch('src.ai_orchestrator.Anthropic')
    def test_decide_action_calls_anthropic(self, mock_anthropic_class, mock_config):
        """Test: decide_next_action llama a Anthropic correctamente."""
        mock_config.DEFAULT_AI_PROVIDER = "anthropic"
        mock_config.ANTHROPIC_API_KEY = "sk-ant-test"
        mock_config.ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"

        mock_tool_use = Mock()
        mock_tool_use.type = "tool_use"
        mock_tool_use.id = "toolu_123"
        mock_tool_use.name = "go_back"
        mock_tool_use.input = {}

        mock_message = Mock()
        mock_message.content = [mock_tool_use]
        mock_message.stop_reason = "tool_use"
        mock_message.model = "claude-3-5-sonnet-20241022"
        mock_message.usage = Mock(input_tokens=100, output_tokens=50)

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_message
        mock_anthropic_class.return_value = mock_client

        from src.ai_orchestrator import AIOrchestrator
        orchestrator = AIOrchestrator()

        ui_elements = []
        result = orchestrator.decide_next_action(
            ui_elements=ui_elements,
            current_step="Volver atrás",
            action_history=["Acción previa"],
            objective=None,
        )

        assert result["tool_calls"][0]["name"] == "go_back"
        mock_client.messages.create.assert_called_once()

    @patch('src.ai_orchestrator.Config')
    @patch('src.ai_orchestrator.OpenAI')
    def test_decide_action_updates_stats(self, mock_openai_class, mock_config):
        """Test: decide_next_action actualiza estadísticas."""
        mock_config.DEFAULT_AI_PROVIDER = "openai"
        mock_config.OPENAI_API_KEY = "sk-test"
        mock_config.OPENAI_MODEL = "gpt-4o"

        mock_message = Mock()
        mock_message.content = "Completado"
        mock_message.tool_calls = None

        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"

        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.model = "gpt-4o"
        mock_response.usage = Mock(prompt_tokens=100, completion_tokens=50, total_tokens=150)

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        from src.ai_orchestrator import AIOrchestrator
        orchestrator = AIOrchestrator()

        # Hacer varias llamadas
        orchestrator.decide_next_action([], "paso 1", [], None)
        orchestrator.decide_next_action([], "paso 2", [], None)

        stats = orchestrator.get_stats()
        assert stats["total_calls"] == 2
        assert stats["successful_calls"] == 2
        assert stats["total_tokens_used"] == 300  # 150 * 2


class TestGetStats:
    """Tests para get_stats()."""

    @patch('src.ai_orchestrator.Config')
    @patch('src.ai_orchestrator.OpenAI')
    def test_stats_initial(self, mock_openai, mock_config):
        """Test: Estadísticas iniciales."""
        mock_config.DEFAULT_AI_PROVIDER = "openai"
        mock_config.OPENAI_API_KEY = "sk-test"
        mock_config.OPENAI_MODEL = "gpt-4o"

        from src.ai_orchestrator import AIOrchestrator
        orchestrator = AIOrchestrator()

        stats = orchestrator.get_stats()

        assert stats["total_calls"] == 0
        assert stats["successful_calls"] == 0
        assert stats["failed_calls"] == 0
        assert stats["total_tokens_used"] == 0

    @patch('src.ai_orchestrator.Config')
    @patch('src.ai_orchestrator.OpenAI')
    def test_stats_with_success_rate(self, mock_openai_class, mock_config):
        """Test: Estadísticas con success rate calculado."""
        mock_config.DEFAULT_AI_PROVIDER = "openai"
        mock_config.OPENAI_API_KEY = "sk-test"
        mock_config.OPENAI_MODEL = "gpt-4o"

        mock_message = Mock()
        mock_message.content = "OK"
        mock_message.tool_calls = None

        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"

        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.model = "gpt-4o"
        mock_response.usage = Mock(prompt_tokens=50, completion_tokens=25, total_tokens=75)

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        from src.ai_orchestrator import AIOrchestrator
        orchestrator = AIOrchestrator()

        # Simular llamadas
        orchestrator.decide_next_action([], "test", [], None)

        stats = orchestrator.get_stats()
        assert "success_rate" in stats
        assert stats["success_rate"] == "100.0%"
