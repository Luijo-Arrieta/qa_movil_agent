"""
Tests unitarios para AppiumSkills (agent_tools.py).
Usa mocks para el driver de Appium y UIParser.
"""

import logging
import pytest
from unittest.mock import Mock, MagicMock, patch

from src.agent_tools import AppiumSkills
from src.ui_parser import UIParser

logger = logging.getLogger(__name__)


class TestAppiumSkillsInit:
    """Tests para la inicialización de AppiumSkills."""

    def test_init_success(self):
        """Test: Inicialización exitosa con driver válido."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session-123"
        mock_ui_parser = Mock(spec=UIParser)

        skills = AppiumSkills(mock_driver, mock_ui_parser)

        assert skills.driver == mock_driver
        assert skills.ui_parser == mock_ui_parser
        assert skills.default_wait_timeout == 5
        assert skills.min_wait_timeout == 0.3
        assert skills._current_app_package is None

    def test_init_with_invalid_driver(self):
        """Test: Inicialización falla si el driver no tiene session_id."""
        mock_driver = Mock()
        mock_driver.session_id = property(fget=lambda x: (_ for _ in ()).throw(Exception("No session")))
        del mock_driver.session_id
        mock_driver.configure_mock(**{"session_id": Mock(side_effect=Exception("No session"))})
        mock_ui_parser = Mock(spec=UIParser)

        # El driver lanza excepción al acceder session_id
        mock_driver_bad = Mock()
        type(mock_driver_bad).session_id = property(lambda self: (_ for _ in ()).throw(Exception("No session")))
        
        with pytest.raises(Exception):
            AppiumSkills(mock_driver_bad, mock_ui_parser)


class TestGetScreenTree:
    """Tests para get_screen_tree()."""

    def test_get_screen_tree_success(self):
        """Test: Obtener page_source exitosamente."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_driver.page_source = "<hierarchy><android.widget.Button/></hierarchy>"
        mock_ui_parser = Mock(spec=UIParser)

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        result = skills.get_screen_tree()

        assert result == "<hierarchy><android.widget.Button/></hierarchy>"
        assert mock_driver.page_source  # Verificar que se accedió

    def test_get_screen_tree_empty_warning(self):
        """Test: Warning cuando page_source es muy corto."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_driver.page_source = "<h/>"  # Muy corto
        mock_ui_parser = Mock(spec=UIParser)

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        result = skills.get_screen_tree()

        assert result == "<h/>"

    def test_get_screen_tree_driver_error(self):
        """Test: Error cuando driver falla al obtener page_source."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        type(mock_driver).page_source = property(
            lambda self: (_ for _ in ()).throw(Exception("Driver error"))
        )
        mock_ui_parser = Mock(spec=UIParser)

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        
        with pytest.raises(Exception) as exc_info:
            skills.get_screen_tree()
        assert "Driver error" in str(exc_info.value)


class TestTouchElementById:
    """Tests para touch_element_by_id()."""

    def test_touch_element_success(self):
        """Test: Click exitoso en elemento por ID."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_element = Mock()
        mock_driver.find_element.return_value = mock_element

        mock_ui_parser = Mock(spec=UIParser)
        mock_ui_parser.get_element_by_id.return_value = "//android.widget.Button[@text='Login']"
        mock_ui_parser.element_map = {0: "//android.widget.Button[@text='Login']"}

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        result = skills.touch_element_by_id(0)

        assert "Success" in result
        mock_element.click.assert_called_once()
        mock_ui_parser.get_element_by_id.assert_called_with(0)

    def test_touch_element_not_found_in_map(self):
        """Test: Error cuando elemento no está en el mapeo."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"

        mock_ui_parser = Mock(spec=UIParser)
        mock_ui_parser.get_element_by_id.return_value = None
        mock_ui_parser.element_map = {}

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        result = skills.touch_element_by_id(99)

        assert "Error" in result
        assert "99" in result

    def test_touch_element_not_found_in_ui(self):
        """Test: Error cuando elemento no existe en la UI."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_driver.find_element.side_effect = Exception("NoSuchElementException")

        mock_ui_parser = Mock(spec=UIParser)
        mock_ui_parser.get_element_by_id.return_value = "//android.widget.Button[@text='Gone']"
        mock_ui_parser.element_map = {0: "//android.widget.Button[@text='Gone']"}

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        result = skills.touch_element_by_id(0)

        assert "Error" in result
        assert "Could not click" in result

    def test_touch_element_stats_updated(self):
        """Test: Estadísticas se actualizan correctamente."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_element = Mock()
        mock_driver.find_element.return_value = mock_element

        mock_ui_parser = Mock(spec=UIParser)
        mock_ui_parser.get_element_by_id.return_value = "//button"
        mock_ui_parser.element_map = {0: "//button"}

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        skills.touch_element_by_id(0)

        stats = skills.get_action_stats()
        assert stats["total_actions"] == 1
        assert stats["successful_actions"] == 1
        assert stats["actions_by_type"]["touch_element_by_id"] == 1


class TestTouchElementByText:
    """Tests para touch_element_by_text()."""

    def test_touch_by_text_success(self):
        """Test: Click exitoso por texto."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_element = Mock()
        mock_driver.find_element.return_value = mock_element
        mock_ui_parser = Mock(spec=UIParser)

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        result = skills.touch_element_by_text("Login")

        assert "Success" in result
        mock_element.click.assert_called_once()

    def test_touch_by_text_not_found(self):
        """Test: Error cuando texto no se encuentra."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_driver.find_element.side_effect = Exception("Element not found")
        mock_ui_parser = Mock(spec=UIParser)

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        result = skills.touch_element_by_text("NonExistent")

        assert "Error" in result


class TestFillFieldById:
    """Tests para fill_field_by_id()."""

    def test_fill_field_success(self):
        """Test: Escribir texto exitosamente."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_driver.is_keyboard_shown.return_value = True
        mock_element = Mock()
        mock_driver.find_element.return_value = mock_element

        mock_ui_parser = Mock(spec=UIParser)
        mock_ui_parser.get_element_by_id.return_value = "//android.widget.EditText[@resource-id='email']"
        mock_ui_parser.element_map = {0: "//android.widget.EditText[@resource-id='email']"}

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        result = skills.fill_field_by_id(0, "test@email.com")

        assert "Success" in result
        mock_element.click.assert_called_once()
        mock_element.clear.assert_called_once()
        mock_element.send_keys.assert_called_once_with("test@email.com")

    def test_fill_field_not_found_in_map(self):
        """Test: Error cuando campo no está en el mapeo."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"

        mock_ui_parser = Mock(spec=UIParser)
        mock_ui_parser.get_element_by_id.return_value = None
        mock_ui_parser.element_map = {}

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        result = skills.fill_field_by_id(99, "value")

        assert "Error" in result
        assert "99" in result

    def test_fill_field_driver_error(self):
        """Test: Error cuando driver falla."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_driver.find_element.side_effect = Exception("Element not found")

        mock_ui_parser = Mock(spec=UIParser)
        mock_ui_parser.get_element_by_id.return_value = "//input"
        mock_ui_parser.element_map = {0: "//input"}

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        result = skills.fill_field_by_id(0, "value")

        assert "Error" in result


class TestFillField:
    """Tests para fill_field() (búsqueda por hint)."""

    def test_fill_field_by_hint_success(self):
        """Test: Escribir en campo por hint."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_driver.is_keyboard_shown.return_value = False
        mock_element = Mock()
        mock_driver.find_element.return_value = mock_element
        mock_ui_parser = Mock(spec=UIParser)

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        result = skills.fill_field("Usuario", "admin")

        assert "Success" in result
        mock_element.send_keys.assert_called_once_with("admin")

    def test_fill_field_by_hint_not_found(self):
        """Test: Error cuando hint no se encuentra."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_driver.find_element.side_effect = Exception("Not found")
        mock_ui_parser = Mock(spec=UIParser)

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        result = skills.fill_field("NonExistent", "value")

        assert "Error" in result


class TestScroll:
    """Tests para scroll()."""

    def test_scroll_down_success(self):
        """Test: Scroll down exitoso."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_driver.get_window_size.return_value = {"width": 1080, "height": 1920}
        mock_ui_parser = Mock(spec=UIParser)
    
        skills = AppiumSkills(mock_driver, mock_ui_parser)
        result = skills.scroll_screen("down")
    
        assert isinstance(result, dict)
        assert result["success"] is True
        assert "Success" in result["message"]
        mock_driver.swipe.assert_called_once()
    
    def test_scroll_up_success(self):
        """Test: Scroll up exitoso."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_driver.get_window_size.return_value = {"width": 1080, "height": 1920}
        mock_ui_parser = Mock(spec=UIParser)
    
        skills = AppiumSkills(mock_driver, mock_ui_parser)
        result = skills.scroll_screen("up")
    
        assert isinstance(result, dict)
        assert result["success"] is True
        assert "Success" in result["message"]
    
    def test_scroll_invalid_direction(self):
        """Test: Error con dirección inválida."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_ui_parser = Mock(spec=UIParser)
    
        skills = AppiumSkills(mock_driver, mock_ui_parser)
        result = skills.scroll_screen("left")
    
        assert isinstance(result, dict)
        assert result["success"] is False
        assert "Error" in result["message"]
        assert "left" in result["message"]
    
    def test_scroll_driver_error(self):
        """Test: Error cuando driver falla."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_driver.get_window_size.side_effect = Exception("Driver error")
        mock_ui_parser = Mock(spec=UIParser)
    
        skills = AppiumSkills(mock_driver, mock_ui_parser)
        result = skills.scroll_screen("down")
    
        assert isinstance(result, dict)
        assert result["success"] is False
        assert "Error" in result["message"]


class TestGoBack:
    """Tests para go_back()."""

    def test_go_back_success(self):
        """Test: Botón atrás exitoso."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_ui_parser = Mock(spec=UIParser)

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        result = skills.go_back()

        assert "Success" in result
        mock_driver.back.assert_called_once()

    def test_go_back_driver_error(self):
        """Test: Error cuando driver falla."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_driver.back.side_effect = Exception("Back failed")
        mock_ui_parser = Mock(spec=UIParser)

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        result = skills.go_back()

        assert "Error" in result


class TestHideKeyboard:
    """Tests para hide_keyboard()."""

    def test_hide_keyboard_visible(self):
        """Test: Ocultar teclado cuando está visible."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_driver.is_keyboard_shown.return_value = True
        mock_ui_parser = Mock(spec=UIParser)

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        result = skills.hide_keyboard()

        assert result is True
        mock_driver.hide_keyboard.assert_called_once()

    def test_hide_keyboard_not_visible(self):
        """Test: No hacer nada cuando teclado no está visible."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_driver.is_keyboard_shown.return_value = False
        mock_ui_parser = Mock(spec=UIParser)

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        result = skills.hide_keyboard()

        assert result is False
        mock_driver.hide_keyboard.assert_not_called()

    def test_hide_keyboard_error_handled(self):
        """Test: Error manejado silenciosamente."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_driver.is_keyboard_shown.side_effect = Exception("Keyboard error")
        mock_ui_parser = Mock(spec=UIParser)

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        result = skills.hide_keyboard()

        assert result is False


class TestAssertScreenContains:
    """Tests para assert_screen_contains()."""

    def test_assert_text_found(self):
        """Test: Texto encontrado en pantalla."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_driver.page_source = '<hierarchy><android.widget.TextView text="Welcome"/></hierarchy>'
        mock_ui_parser = Mock(spec=UIParser)

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        is_present, message = skills.assert_screen_contains("Welcome")

        assert is_present is True
        assert "Success" in message

    def test_assert_text_not_found(self):
        """Test: Texto no encontrado en pantalla."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_driver.page_source = '<hierarchy><android.widget.TextView text="Login"/></hierarchy>'
        mock_ui_parser = Mock(spec=UIParser)

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        is_present, message = skills.assert_screen_contains("NonExistent")

        assert is_present is False
        assert "Error" in message

    def test_assert_driver_error(self):
        """Test: Error cuando driver falla."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        type(mock_driver).page_source = property(
            lambda self: (_ for _ in ()).throw(Exception("Driver error"))
        )
        mock_ui_parser = Mock(spec=UIParser)

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        is_present, message = skills.assert_screen_contains("Text")

        assert is_present is False
        assert "Error" in message


class TestDismissPopup:
    """Tests para dismiss_popup()."""

    def test_dismiss_popup_found_ok(self):
        """Test: Popup cerrado con botón OK."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_element = Mock()
        mock_driver.find_element.return_value = mock_element
        mock_ui_parser = Mock(spec=UIParser)

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        result = skills.dismiss_popup()

        assert "Success" in result

    def test_dismiss_popup_not_found(self):
        """Test: No se encontró botón de cierre."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_driver.find_element.side_effect = Exception("Not found")
        mock_ui_parser = Mock(spec=UIParser)

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        result = skills.dismiss_popup()

        assert "Error" in result


class TestMultiAppManagement:
    """Tests para gestión multi-app."""

    def test_query_app_state_foreground(self):
        """Test: Consultar estado de app en foreground."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_driver.query_app_state.return_value = 4  # FOREGROUND
        mock_ui_parser = Mock(spec=UIParser)

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        state, state_name = skills.query_app_state("com.example.app")

        assert state == 4
        assert state_name == "FOREGROUND"

    def test_query_app_state_not_running(self):
        """Test: Consultar estado de app no ejecutándose."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_driver.query_app_state.return_value = 1  # NOT_RUNNING
        mock_ui_parser = Mock(spec=UIParser)

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        state, state_name = skills.query_app_state("com.example.app")

        assert state == 1
        assert state_name == "NOT_RUNNING"

    def test_query_app_state_error(self):
        """Test: Error al consultar estado."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_driver.query_app_state.side_effect = Exception("Query failed")
        mock_ui_parser = Mock(spec=UIParser)

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        state, state_name = skills.query_app_state("com.example.app")

        assert state == -1
        assert "ERROR" in state_name

    def test_activate_app_success(self):
        """Test: Activar app exitosamente."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_driver.query_app_state.return_value = 1  # NOT_RUNNING
        mock_ui_parser = Mock(spec=UIParser)

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        result = skills.activate_app("com.example.app")

        assert "Success" in result
        mock_driver.activate_app.assert_called_once_with("com.example.app")
        assert skills._current_app_package == "com.example.app"

    def test_activate_app_not_installed(self):
        """Test: Error cuando app no está instalada."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_driver.query_app_state.return_value = 0  # NOT_INSTALLED
        mock_ui_parser = Mock(spec=UIParser)

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        result = skills.activate_app("com.example.missing")

        assert "Error" in result
        assert "NO está instalada" in result

    def test_terminate_app_success(self):
        """Test: Terminar app exitosamente."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_driver.terminate_app.return_value = True
        mock_ui_parser = Mock(spec=UIParser)

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        skills._current_app_package = "com.example.app"
        result = skills.terminate_app("com.example.app")

        assert "Success" in result
        mock_driver.terminate_app.assert_called_once_with("com.example.app")
        assert skills._current_app_package is None

    def test_terminate_app_not_running(self):
        """Test: Terminar app que no estaba corriendo."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_driver.terminate_app.return_value = False
        mock_ui_parser = Mock(spec=UIParser)

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        result = skills.terminate_app("com.example.app")

        assert "Success" in result
        assert "was not running" in result

    def test_switch_to_app_terminates_current(self):
        """Test: Switch cierra app actual."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_driver.query_app_state.return_value = 3  # BACKGROUND
        mock_driver.terminate_app.return_value = True
        mock_ui_parser = Mock(spec=UIParser)

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        skills._current_app_package = "com.old.app"
        result = skills.switch_to_app("com.new.app")

        assert "Success" in result
        mock_driver.terminate_app.assert_called_once_with("com.old.app")
        mock_driver.activate_app.assert_called_once_with("com.new.app")

    def test_switch_to_app_keep_background(self):
        """Test: Switch mantiene app en background."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_driver.query_app_state.return_value = 3
        mock_ui_parser = Mock(spec=UIParser)

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        skills._current_app_package = "com.old.app"
        result = skills.switch_to_app_keep_background("com.new.app")

        assert "Success" in result
        assert "background" in result
        mock_driver.terminate_app.assert_not_called()
        mock_driver.activate_app.assert_called_once_with("com.new.app")

    def test_switch_to_same_app(self):
        """Test: Switch a la misma app no hace nada."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_ui_parser = Mock(spec=UIParser)

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        skills._current_app_package = "com.same.app"
        result = skills.switch_to_app_keep_background("com.same.app")

        assert "Success" in result
        assert "already in foreground" in result
        mock_driver.activate_app.assert_not_called()

    def test_get_current_app_package(self):
        """Test: Obtener package de app actual."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_ui_parser = Mock(spec=UIParser)

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        assert skills.get_current_app_package() is None

        skills._current_app_package = "com.test.app"
        assert skills.get_current_app_package() == "com.test.app"


class TestActionStats:
    """Tests para estadísticas de acciones."""

    def test_stats_initial_values(self):
        """Test: Valores iniciales de estadísticas."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_ui_parser = Mock(spec=UIParser)

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        stats = skills.get_action_stats()

        assert stats["total_actions"] == 0
        assert stats["successful_actions"] == 0
        assert stats["failed_actions"] == 0
        assert stats["actions_by_type"] == {}

    def test_stats_after_multiple_actions(self):
        """Test: Estadísticas después de varias acciones."""
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_driver.get_window_size.return_value = {"width": 1080, "height": 1920}
        mock_ui_parser = Mock(spec=UIParser)

        skills = AppiumSkills(mock_driver, mock_ui_parser)
        skills.scroll("down")
        skills.scroll("up")
        skills.go_back()

        stats = skills.get_action_stats()
        assert stats["total_actions"] == 3
        assert stats["successful_actions"] == 3
        assert "success_rate" in stats
        assert stats["actions_by_type"]["scroll"] == 2
        assert stats["actions_by_type"]["go_back"] == 1
