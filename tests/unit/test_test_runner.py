"""
Tests unitarios para AITestRunner (test_runner.py).
Usa mocks para driver, UIParser, AppiumSkills y AIOrchestrator.
"""

import logging
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

logger = logging.getLogger(__name__)


class TestAITestRunnerInit:
    """Tests para la inicialización de AITestRunner."""

    @patch('src.test_runner.AIOrchestrator')
    @patch('src.test_runner.AppiumSkills')
    @patch('src.test_runner.UIParser')
    @patch('src.test_runner.Config')
    def test_init_success(self, mock_config, mock_ui_parser_class, 
                          mock_skills_class, mock_orchestrator_class):
        """Test: Inicialización exitosa."""
        mock_config.validate.return_value = (True, None)
        mock_config.debug_print_config = Mock()

        mock_driver = Mock()
        mock_driver.session_id = "test-session-123"

        from src.test_runner import AITestRunner
        runner = AITestRunner(mock_driver, objective="Test objetivo")

        assert runner.driver == mock_driver
        assert runner.objective == "Test objetivo"
        assert runner.max_retries == 3
        assert runner.action_history == []
        mock_ui_parser_class.assert_called_once()
        mock_skills_class.assert_called_once()
        mock_orchestrator_class.assert_called_once()

    @patch('src.test_runner.Config')
    def test_init_invalid_config(self, mock_config):
        """Test: Error cuando configuración es inválida."""
        mock_config.validate.return_value = (False, "Missing API key")
        mock_config.debug_print_config = Mock()

        mock_driver = Mock()
        mock_driver.session_id = "test-session"

        from src.test_runner import AITestRunner
        with pytest.raises(ValueError) as exc_info:
            AITestRunner(mock_driver)
        assert "Missing API key" in str(exc_info.value)

    @patch('src.test_runner.AIOrchestrator')
    @patch('src.test_runner.AppiumSkills')
    @patch('src.test_runner.UIParser')
    @patch('src.test_runner.Config')
    def test_init_without_objective(self, mock_config, mock_ui_parser, 
                                     mock_skills, mock_orchestrator):
        """Test: Inicialización sin objetivo."""
        mock_config.validate.return_value = (True, None)
        mock_config.debug_print_config = Mock()

        mock_driver = Mock()
        mock_driver.session_id = "test-session"

        from src.test_runner import AITestRunner
        runner = AITestRunner(mock_driver)

        assert runner.objective is None


class TestRunTestPlan:
    """Tests para run_test_plan()."""

    @patch('src.test_runner.AIOrchestrator')
    @patch('src.test_runner.AppiumSkills')
    @patch('src.test_runner.UIParser')
    @patch('src.test_runner.Config')
    def test_run_empty_plan(self, mock_config, mock_ui_parser, 
                            mock_skills, mock_orchestrator):
        """Test: Plan vacío retorna True."""
        mock_config.validate.return_value = (True, None)
        mock_config.debug_print_config = Mock()

        mock_driver = Mock()
        mock_driver.session_id = "test-session"

        from src.test_runner import AITestRunner
        runner = AITestRunner(mock_driver)

        result = runner.run_test_plan([])

        assert result is True

    @patch('src.test_runner.AIOrchestrator')
    @patch('src.test_runner.AppiumSkills')
    @patch('src.test_runner.UIParser')
    @patch('src.test_runner.Config')
    @patch('src.test_runner.time')
    def test_run_single_step_success(self, mock_time, mock_config, mock_ui_parser_class,
                                      mock_skills_class, mock_orchestrator_class):
        """Test: Plan de un paso exitoso."""
        mock_config.validate.return_value = (True, None)
        mock_config.debug_print_config = Mock()
        mock_time.sleep = Mock()
        mock_time.time = Mock(return_value=1000)

        mock_driver = Mock()
        mock_driver.session_id = "test-session"

        # Mock UIParser
        mock_ui_parser = Mock()
        mock_ui_parser.parse_screen.return_value = [
            {"id": 0, "role": "button", "label": "Login", "checked": None}
        ]
        mock_ui_parser_class.return_value = mock_ui_parser

        # Mock AppiumSkills - usar get_screen_tree_stable (el método real usado)
        mock_skills = Mock()
        mock_skills.get_screen_tree_stable.return_value = "<hierarchy/>"
        mock_skills.touch_element_by_id.return_value = "Success: Clicked"
        mock_skills_class.return_value = mock_skills

        # Mock AIOrchestrator - primero tool call, luego completado
        mock_orchestrator = Mock()
        mock_orchestrator.decide_next_action.side_effect = [
            {
                "tool_calls": [{"name": "touch_element_by_id", "arguments": {"element_id": 0}, "id": "1"}],
                "message": None
            },
            {"tool_calls": [], "message": "Paso completado"}
        ]
        mock_orchestrator.get_stats.return_value = {}
        mock_orchestrator_class.return_value = mock_orchestrator

        from src.test_runner import AITestRunner
        runner = AITestRunner(mock_driver)

        result = runner.run_test_plan(["Click en Login"])

        assert result is True

    @patch('src.test_runner.AIOrchestrator')
    @patch('src.test_runner.AppiumSkills')
    @patch('src.test_runner.UIParser')
    @patch('src.test_runner.Config')
    @patch('src.test_runner.time')
    def test_run_step_failure_after_retries(self, mock_time, mock_config, 
                                             mock_ui_parser_class, mock_skills_class, 
                                             mock_orchestrator_class):
        """Test: Paso falla después de reintentos."""
        mock_config.validate.return_value = (True, None)
        mock_config.debug_print_config = Mock()
        mock_time.sleep = Mock()
        mock_time.time = Mock(return_value=1000)

        mock_driver = Mock()
        mock_driver.session_id = "test-session"

        mock_ui_parser = Mock()
        mock_ui_parser.parse_screen.return_value = []
        mock_ui_parser.debug_dump_element_map = Mock()
        mock_ui_parser_class.return_value = mock_ui_parser

        mock_skills = Mock()
        mock_skills.get_screen_tree_stable.return_value = "<hierarchy/>"
        mock_skills.touch_element_by_id.return_value = "Error: Element not found"
        mock_skills.get_action_stats.return_value = {}
        mock_skills_class.return_value = mock_skills

        mock_orchestrator = Mock()
        mock_orchestrator.decide_next_action.return_value = {
            "tool_calls": [{"name": "touch_element_by_id", "arguments": {"element_id": 99}, "id": "1"}],
            "message": None
        }
        mock_orchestrator.get_stats.return_value = {}
        mock_orchestrator_class.return_value = mock_orchestrator

        from src.test_runner import AITestRunner
        runner = AITestRunner(mock_driver)

        result = runner.run_test_plan(["Click en elemento inexistente"])

        assert result is False


class TestExecuteSingleToolCall:
    """Tests para _execute_single_tool_call()."""

    @patch('src.test_runner.AIOrchestrator')
    @patch('src.test_runner.AppiumSkills')
    @patch('src.test_runner.UIParser')
    @patch('src.test_runner.Config')
    def test_execute_touch_element_by_id(self, mock_config, mock_ui_parser_class,
                                          mock_skills_class, mock_orchestrator_class):
        """Test: Ejecutar touch_element_by_id."""
        mock_config.validate.return_value = (True, None)
        mock_config.debug_print_config = Mock()

        mock_driver = Mock()
        mock_driver.session_id = "test-session"

        mock_skills = Mock()
        mock_skills.touch_element_by_id.return_value = "Success: Clicked"
        mock_skills_class.return_value = mock_skills

        from src.test_runner import AITestRunner
        runner = AITestRunner(mock_driver)

        tool_call = {"name": "touch_element_by_id", "arguments": {"element_id": 5}, "id": "1"}
        result = runner._execute_single_tool_call(tool_call, "test step")

        assert result is True
        mock_skills.touch_element_by_id.assert_called_once_with(5)

    @patch('src.test_runner.AIOrchestrator')
    @patch('src.test_runner.AppiumSkills')
    @patch('src.test_runner.UIParser')
    @patch('src.test_runner.Config')
    def test_execute_fill_field_by_id(self, mock_config, mock_ui_parser_class,
                                       mock_skills_class, mock_orchestrator_class):
        """Test: Ejecutar fill_field_by_id."""
        mock_config.validate.return_value = (True, None)
        mock_config.debug_print_config = Mock()

        mock_driver = Mock()
        mock_driver.session_id = "test-session"

        mock_skills = Mock()
        mock_skills.fill_field_by_id.return_value = "Success: Typed"
        mock_skills_class.return_value = mock_skills

        from src.test_runner import AITestRunner
        runner = AITestRunner(mock_driver)

        tool_call = {
            "name": "fill_field_by_id", 
            "arguments": {"element_id": 2, "value": "test@email.com"},
            "id": "1"
        }
        result = runner._execute_single_tool_call(tool_call, "test step")

        assert result is True
        mock_skills.fill_field_by_id.assert_called_once_with(2, "test@email.com")

    @patch('src.test_runner.AIOrchestrator')
    @patch('src.test_runner.AppiumSkills')
    @patch('src.test_runner.UIParser')
    @patch('src.test_runner.Config')
    def test_execute_scroll(self, mock_config, mock_ui_parser_class,
                            mock_skills_class, mock_orchestrator_class):
        """Test: Ejecutar scroll."""
        mock_config.validate.return_value = (True, None)
        mock_config.debug_print_config = Mock()

        mock_driver = Mock()
        mock_driver.session_id = "test-session"

        mock_skills = Mock()
        mock_skills.scroll.return_value = "Success: Scrolled down"
        mock_skills_class.return_value = mock_skills

        from src.test_runner import AITestRunner
        runner = AITestRunner(mock_driver)

        tool_call = {"name": "scroll", "arguments": {"direction": "down"}, "id": "1"}
        result = runner._execute_single_tool_call(tool_call, "test step")

        assert result is True
        mock_skills.scroll.assert_called_once_with("down")

    @patch('src.test_runner.AIOrchestrator')
    @patch('src.test_runner.AppiumSkills')
    @patch('src.test_runner.UIParser')
    @patch('src.test_runner.Config')
    def test_execute_go_back(self, mock_config, mock_ui_parser_class,
                             mock_skills_class, mock_orchestrator_class):
        """Test: Ejecutar go_back."""
        mock_config.validate.return_value = (True, None)
        mock_config.debug_print_config = Mock()

        mock_driver = Mock()
        mock_driver.session_id = "test-session"

        mock_skills = Mock()
        mock_skills.go_back.return_value = "Success: Back pressed"
        mock_skills_class.return_value = mock_skills

        from src.test_runner import AITestRunner
        runner = AITestRunner(mock_driver)

        tool_call = {"name": "go_back", "arguments": {}, "id": "1"}
        result = runner._execute_single_tool_call(tool_call, "test step")

        assert result is True
        mock_skills.go_back.assert_called_once()

    @patch('src.test_runner.AIOrchestrator')
    @patch('src.test_runner.AppiumSkills')
    @patch('src.test_runner.UIParser')
    @patch('src.test_runner.Config')
    def test_execute_assert_screen_contains_success(self, mock_config, mock_ui_parser_class,
                                                     mock_skills_class, mock_orchestrator_class):
        """Test: Ejecutar assert_screen_contains exitoso."""
        mock_config.validate.return_value = (True, None)
        mock_config.debug_print_config = Mock()

        mock_driver = Mock()
        mock_driver.session_id = "test-session"

        # Usar MagicMock con unsafe=True para permitir métodos que empiezan con "assert_"
        mock_skills = MagicMock(unsafe=True)
        mock_skills.assert_screen_contains.return_value = (True, "Success: Text found")
        mock_skills_class.return_value = mock_skills

        from src.test_runner import AITestRunner
        runner = AITestRunner(mock_driver)

        tool_call = {"name": "assert_screen_contains", "arguments": {"text": "Welcome"}, "id": "1"}
        result = runner._execute_single_tool_call(tool_call, "test step")

        assert result is True
        mock_skills.assert_screen_contains.assert_called_once_with("Welcome")

    @patch('src.test_runner.AIOrchestrator')
    @patch('src.test_runner.AppiumSkills')
    @patch('src.test_runner.UIParser')
    @patch('src.test_runner.Config')
    def test_execute_assert_screen_contains_failure(self, mock_config, mock_ui_parser_class,
                                                     mock_skills_class, mock_orchestrator_class):
        """Test: Ejecutar assert_screen_contains fallido."""
        mock_config.validate.return_value = (True, None)
        mock_config.debug_print_config = Mock()

        mock_driver = Mock()
        mock_driver.session_id = "test-session"

        # Usar MagicMock con unsafe=True para permitir métodos que empiezan con "assert_"
        mock_skills = MagicMock(unsafe=True)
        mock_skills.assert_screen_contains.return_value = (False, "Error: Text not found")
        mock_skills_class.return_value = mock_skills

        from src.test_runner import AITestRunner
        runner = AITestRunner(mock_driver)

        tool_call = {"name": "assert_screen_contains", "arguments": {"text": "Missing"}, "id": "1"}
        result = runner._execute_single_tool_call(tool_call, "test step")

        assert result is False

    @patch('src.test_runner.AIOrchestrator')
    @patch('src.test_runner.AppiumSkills')
    @patch('src.test_runner.UIParser')
    @patch('src.test_runner.Config')
    def test_execute_unknown_tool(self, mock_config, mock_ui_parser_class,
                                   mock_skills_class, mock_orchestrator_class):
        """Test: Herramienta desconocida retorna False."""
        mock_config.validate.return_value = (True, None)
        mock_config.debug_print_config = Mock()

        mock_driver = Mock()
        mock_driver.session_id = "test-session"

        from src.test_runner import AITestRunner
        runner = AITestRunner(mock_driver)

        tool_call = {"name": "unknown_tool", "arguments": {}, "id": "1"}
        result = runner._execute_single_tool_call(tool_call, "test step")

        assert result is False

    @patch('src.test_runner.AIOrchestrator')
    @patch('src.test_runner.AppiumSkills')
    @patch('src.test_runner.UIParser')
    @patch('src.test_runner.Config')
    def test_execute_missing_element_id(self, mock_config, mock_ui_parser_class,
                                         mock_skills_class, mock_orchestrator_class):
        """Test: Falta element_id retorna False."""
        mock_config.validate.return_value = (True, None)
        mock_config.debug_print_config = Mock()

        mock_driver = Mock()
        mock_driver.session_id = "test-session"

        from src.test_runner import AITestRunner
        runner = AITestRunner(mock_driver)

        tool_call = {"name": "touch_element_by_id", "arguments": {}, "id": "1"}
        result = runner._execute_single_tool_call(tool_call, "test step")

        assert result is False


class TestMultiAppToolCalls:
    """Tests para tool calls de gestión multi-app."""

    @patch('src.test_runner.AIOrchestrator')
    @patch('src.test_runner.AppiumSkills')
    @patch('src.test_runner.UIParser')
    @patch('src.test_runner.Config')
    def test_execute_activate_app(self, mock_config, mock_ui_parser_class,
                                   mock_skills_class, mock_orchestrator_class):
        """Test: Ejecutar activate_app."""
        mock_config.validate.return_value = (True, None)
        mock_config.debug_print_config = Mock()

        mock_driver = Mock()
        mock_driver.session_id = "test-session"

        mock_skills = Mock()
        mock_skills.activate_app.return_value = "Success: Activated"
        mock_skills_class.return_value = mock_skills

        from src.test_runner import AITestRunner
        runner = AITestRunner(mock_driver)

        tool_call = {"name": "activate_app", "arguments": {"app_package": "com.test.app"}, "id": "1"}
        result = runner._execute_single_tool_call(tool_call, "test step")

        assert result is True
        mock_skills.activate_app.assert_called_once_with("com.test.app")

    @patch('src.test_runner.AIOrchestrator')
    @patch('src.test_runner.AppiumSkills')
    @patch('src.test_runner.UIParser')
    @patch('src.test_runner.Config')
    def test_execute_terminate_app(self, mock_config, mock_ui_parser_class,
                                    mock_skills_class, mock_orchestrator_class):
        """Test: Ejecutar terminate_app."""
        mock_config.validate.return_value = (True, None)
        mock_config.debug_print_config = Mock()

        mock_driver = Mock()
        mock_driver.session_id = "test-session"

        mock_skills = Mock()
        mock_skills.terminate_app.return_value = "Success: Terminated"
        mock_skills_class.return_value = mock_skills

        from src.test_runner import AITestRunner
        runner = AITestRunner(mock_driver)

        tool_call = {"name": "terminate_app", "arguments": {"app_package": "com.test.app"}, "id": "1"}
        result = runner._execute_single_tool_call(tool_call, "test step")

        assert result is True
        mock_skills.terminate_app.assert_called_once_with("com.test.app")

    @patch('src.test_runner.AIOrchestrator')
    @patch('src.test_runner.AppiumSkills')
    @patch('src.test_runner.UIParser')
    @patch('src.test_runner.Config')
    def test_execute_switch_to_app(self, mock_config, mock_ui_parser_class,
                                    mock_skills_class, mock_orchestrator_class):
        """Test: Ejecutar switch_to_app."""
        mock_config.validate.return_value = (True, None)
        mock_config.debug_print_config = Mock()

        mock_driver = Mock()
        mock_driver.session_id = "test-session"

        mock_skills = Mock()
        mock_skills.switch_to_app.return_value = "Success: Switched"
        mock_skills_class.return_value = mock_skills

        from src.test_runner import AITestRunner
        runner = AITestRunner(mock_driver)

        tool_call = {"name": "switch_to_app", "arguments": {"app_package": "com.new.app"}, "id": "1"}
        result = runner._execute_single_tool_call(tool_call, "test step")

        assert result is True
        mock_skills.switch_to_app.assert_called_once_with("com.new.app")

    @patch('src.test_runner.AIOrchestrator')
    @patch('src.test_runner.AppiumSkills')
    @patch('src.test_runner.UIParser')
    @patch('src.test_runner.Config')
    def test_execute_switch_to_app_keep_background(self, mock_config, mock_ui_parser_class,
                                                    mock_skills_class, mock_orchestrator_class):
        """Test: Ejecutar switch_to_app_keep_background."""
        mock_config.validate.return_value = (True, None)
        mock_config.debug_print_config = Mock()

        mock_driver = Mock()
        mock_driver.session_id = "test-session"

        mock_skills = Mock()
        mock_skills.switch_to_app_keep_background.return_value = "Success: Switched (background)"
        mock_skills_class.return_value = mock_skills

        from src.test_runner import AITestRunner
        runner = AITestRunner(mock_driver)

        tool_call = {
            "name": "switch_to_app_keep_background", 
            "arguments": {"app_package": "com.new.app"}, 
            "id": "1"
        }
        result = runner._execute_single_tool_call(tool_call, "test step")

        assert result is True
        mock_skills.switch_to_app_keep_background.assert_called_once_with("com.new.app")

    @patch('src.test_runner.AIOrchestrator')
    @patch('src.test_runner.AppiumSkills')
    @patch('src.test_runner.UIParser')
    @patch('src.test_runner.Config')
    def test_execute_app_tool_missing_package(self, mock_config, mock_ui_parser_class,
                                               mock_skills_class, mock_orchestrator_class):
        """Test: Falta app_package retorna False."""
        mock_config.validate.return_value = (True, None)
        mock_config.debug_print_config = Mock()

        mock_driver = Mock()
        mock_driver.session_id = "test-session"

        from src.test_runner import AITestRunner
        runner = AITestRunner(mock_driver)

        tool_call = {"name": "activate_app", "arguments": {}, "id": "1"}
        result = runner._execute_single_tool_call(tool_call, "test step")

        assert result is False


class TestClearHistory:
    """Tests para clear_history()."""

    @patch('src.test_runner.AIOrchestrator')
    @patch('src.test_runner.AppiumSkills')
    @patch('src.test_runner.UIParser')
    @patch('src.test_runner.Config')
    def test_clear_history(self, mock_config, mock_ui_parser,
                           mock_skills, mock_orchestrator):
        """Test: Limpiar historial."""
        mock_config.validate.return_value = (True, None)
        mock_config.debug_print_config = Mock()

        mock_driver = Mock()
        mock_driver.session_id = "test-session"

        from src.test_runner import AITestRunner
        runner = AITestRunner(mock_driver)
        runner.action_history = ["Acción 1", "Acción 2", "Acción 3"]

        runner.clear_history()

        assert runner.action_history == []


class TestGetExecutionStats:
    """Tests para get_execution_stats()."""

    @patch('src.test_runner.AIOrchestrator')
    @patch('src.test_runner.AppiumSkills')
    @patch('src.test_runner.UIParser')
    @patch('src.test_runner.Config')
    def test_get_execution_stats(self, mock_config, mock_ui_parser_class,
                                  mock_skills_class, mock_orchestrator_class):
        """Test: Obtener estadísticas de ejecución."""
        mock_config.validate.return_value = (True, None)
        mock_config.debug_print_config = Mock()

        mock_driver = Mock()
        mock_driver.session_id = "test-session"

        mock_orchestrator = Mock()
        mock_orchestrator.get_stats.return_value = {"total_calls": 5}
        mock_orchestrator_class.return_value = mock_orchestrator

        mock_skills = Mock()
        mock_skills.get_action_stats.return_value = {"total_actions": 10}
        mock_skills_class.return_value = mock_skills

        from src.test_runner import AITestRunner
        runner = AITestRunner(mock_driver)
        runner.action_history = ["a1", "a2"]

        stats = runner.get_execution_stats()

        assert stats["action_history_count"] == 2
        assert "elapsed_time" in stats
        assert "ai_orchestrator" in stats
        assert "agent_tools" in stats


class TestDebugDumpState:
    """Tests para debug_dump_state()."""

    @patch('src.test_runner.AIOrchestrator')
    @patch('src.test_runner.AppiumSkills')
    @patch('src.test_runner.UIParser')
    @patch('src.test_runner.Config')
    def test_debug_dump_state(self, mock_config, mock_ui_parser_class,
                               mock_skills_class, mock_orchestrator_class):
        """Test: Debug dump no lanza excepciones."""
        mock_config.validate.return_value = (True, None)
        mock_config.debug_print_config = Mock()

        mock_driver = Mock()
        mock_driver.session_id = "test-session"

        mock_ui_parser = Mock()
        mock_ui_parser.element_map = {0: "//button", 1: "//input"}
        mock_ui_parser.current_id = 2
        mock_ui_parser_class.return_value = mock_ui_parser

        from src.test_runner import AITestRunner
        runner = AITestRunner(mock_driver, objective="Test objetivo")
        runner.action_history = ["Acción de prueba"]

        # No debe lanzar excepción
        runner.debug_dump_state()


class TestToolCallWithError:
    """Tests para manejo de errores en tool calls."""

    @patch('src.test_runner.AIOrchestrator')
    @patch('src.test_runner.AppiumSkills')
    @patch('src.test_runner.UIParser')
    @patch('src.test_runner.Config')
    def test_tool_call_returns_error(self, mock_config, mock_ui_parser_class,
                                      mock_skills_class, mock_orchestrator_class):
        """Test: Tool call que retorna Error."""
        mock_config.validate.return_value = (True, None)
        mock_config.debug_print_config = Mock()

        mock_driver = Mock()
        mock_driver.session_id = "test-session"

        mock_skills = Mock()
        mock_skills.touch_element_by_id.return_value = "Error: Element not found"
        mock_skills_class.return_value = mock_skills

        from src.test_runner import AITestRunner
        runner = AITestRunner(mock_driver)

        tool_call = {"name": "touch_element_by_id", "arguments": {"element_id": 0}, "id": "1"}
        result = runner._execute_single_tool_call(tool_call, "test step")

        assert result is False

    @patch('src.test_runner.AIOrchestrator')
    @patch('src.test_runner.AppiumSkills')
    @patch('src.test_runner.UIParser')
    @patch('src.test_runner.Config')
    def test_tool_call_raises_exception(self, mock_config, mock_ui_parser_class,
                                         mock_skills_class, mock_orchestrator_class):
        """Test: Tool call que lanza excepción."""
        mock_config.validate.return_value = (True, None)
        mock_config.debug_print_config = Mock()

        mock_driver = Mock()
        mock_driver.session_id = "test-session"

        mock_skills = Mock()
        mock_skills.scroll.side_effect = Exception("Unexpected error")
        mock_skills_class.return_value = mock_skills

        from src.test_runner import AITestRunner
        runner = AITestRunner(mock_driver)

        tool_call = {"name": "scroll", "arguments": {"direction": "down"}, "id": "1"}
        result = runner._execute_single_tool_call(tool_call, "test step")

        assert result is False
