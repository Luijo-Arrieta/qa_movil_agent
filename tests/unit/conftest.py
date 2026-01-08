"""
Fixtures específicos para tests unitarios.

Este archivo contiene fixtures que NO requieren Appium ni dispositivo.
Principalmente fixtures para mocks y datos de prueba.
"""

import pytest


@pytest.fixture
def sample_xml_login_screen():
    """
    XML de ejemplo que representa una pantalla de login típica.
    Útil para tests de UIParser.
    """
    return """
    <hierarchy rotation="0">
        <android.widget.FrameLayout 
            index="0" 
            class="android.widget.FrameLayout"
            package="com.example.app">
            <android.widget.EditText
                index="0"
                text=""
                resource-id="com.example:id/email_input"
                class="android.widget.EditText"
                content-desc=""
                hint="Email"
                checkable="false"
                checked="false"
                clickable="true"
                enabled="true"
                focusable="true"
                focused="false"/>
            <android.widget.EditText
                index="1"
                text=""
                resource-id="com.example:id/password_input"
                class="android.widget.EditText"
                content-desc=""
                hint="Password"
                checkable="false"
                checked="false"
                clickable="true"
                enabled="true"
                focusable="true"
                focused="false"/>
            <android.widget.Button
                index="2"
                text="Login"
                resource-id="com.example:id/login_button"
                class="android.widget.Button"
                content-desc=""
                checkable="false"
                checked="false"
                clickable="true"
                enabled="true"
                focusable="true"
                focused="false"/>
            <android.widget.CheckBox
                index="3"
                text="Remember me"
                resource-id="com.example:id/remember_checkbox"
                class="android.widget.CheckBox"
                checkable="true"
                checked="false"
                clickable="true"
                enabled="true"/>
        </android.widget.FrameLayout>
    </hierarchy>
    """


@pytest.fixture
def sample_xml_empty_screen():
    """XML de ejemplo con pantalla vacía (sin elementos interactuables)."""
    return """
    <hierarchy rotation="0">
        <android.widget.FrameLayout 
            class="android.widget.FrameLayout"
            package="com.example.app">
            <android.widget.LinearLayout class="android.widget.LinearLayout">
                <android.widget.TextView text="Loading..." class="android.widget.TextView"/>
            </android.widget.LinearLayout>
        </android.widget.FrameLayout>
    </hierarchy>
    """


@pytest.fixture
def sample_elements():
    """Lista de elementos de ejemplo ya parseados."""
    return [
        {"id": 0, "role": "input", "label": "com.example:id/email_input", "checked": None},
        {"id": 1, "role": "input", "label": "com.example:id/password_input", "checked": None},
        {"id": 2, "role": "button", "label": "com.example:id/login_button", "checked": None},
        {"id": 3, "role": "checkbox", "label": "com.example:id/remember_checkbox", "checked": False},
    ]
