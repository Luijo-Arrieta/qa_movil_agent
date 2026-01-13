# Documentación de AutoDroid-AI Agent

Bienvenido a la documentación completa del proyecto **AutoDroid-AI Agent**, un agente de inteligencia artificial autónomo para pruebas móviles en Android.

## ¿Qué es AutoDroid-AI Agent?

Es una herramienta que te permite escribir pruebas automáticas para aplicaciones Android **usando lenguaje natural**. En lugar de escribir código complicado con selectores XPath, simplemente describes lo que quieres hacer:

```txt
"Ingresar el usuario juan@example.com"
"Hacer clic en el botón Iniciar Sesión"
"Verificar que aparezca el texto Bienvenido"
```

La inteligencia artificial (GPT-4 o Claude) analiza la pantalla del celular y ejecuta las acciones automáticamente.

## ¿Cómo funciona?

```txt
┌─────────────────────────────────────────────────────────────────┐
│  1. Tú escribes instrucciones en español                        │
│     "Hacer clic en el botón Ingresar"                          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. El agente obtiene la pantalla actual del celular           │
│     (una "foto" de todos los elementos visibles)               │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. La IA analiza la pantalla y decide qué hacer               │
│     "Veo un botón que dice 'Ingresar', voy a tocarlo"          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. El agente ejecuta la acción en el celular                  │
│     ✓ Clic ejecutado exitosamente                              │
└─────────────────────────────────────────────────────────────────┘
```

## Tabla de Contenidos

### Primeros Pasos

| Documento | Descripción | Tiempo estimado |
|-----------|-------------|-----------------|
| [Inicio Rápido](01-quick-start.md) | Corre tu primera prueba en 5 minutos | 5 min |
| [Glosario](02-glossary.md) | Explicación de términos técnicos | Referencia |

### Instalación

| Documento | Descripción | Tiempo estimado |
|-----------|-------------|-----------------|
| [Prerequisitos](05-prerequisites.md) | Todo lo que necesitas instalar | Referencia |
| [Instalación en Windows](03-installation-windows.md) | Guía paso a paso para Windows | 30-45 min |
| [Instalación en Ubuntu](04-installation-ubuntu.md) | Guía paso a paso para Ubuntu/Linux | 30-45 min |

### Uso Avanzado

| Documento | Descripción | Tiempo estimado |
|-----------|-------------|-----------------|
| [Crear Pruebas](06-creating-tests.md) | Cómo escribir tus propias pruebas | 20 min |

## ¿Por dónde empiezo?

1. **Si es tu primera vez**: Empieza por el [Glosario](02-glossary.md) para familiarizarte con los términos
2. **Si quieres instalar**: Ve a [Prerequisitos](05-prerequisites.md) y luego a la guía de tu sistema operativo
3. **Si ya tienes todo instalado**: Ve directo al [Inicio Rápido](01-quick-start.md) y ejecuta `tests/specs/examples/test_example.py` para ver ejemplos funcionales
4. **Si quieres crear tus propias pruebas**: Lee [Crear Pruebas](06-creating-tests.md) - incluye ejemplos con AITestRunner (recomendado) y UIParser (avanzado)

## Arquitectura del Sistema

El sistema está compuesto por 5 módulos principales que trabajan en secuencia:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ARQUITECTURA                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐         │
│   │              │    │              │    │                      │         │
│   │  Test Runner │───▶│   UIParser   │───▶│   AI Orchestrator    │         │
│   │              │    │              │    │   (GPT-4 / Claude)   │         │
│   └──────────────┘    └──────────────┘    └──────────────────────┘         │
│          │                   │                       │                      │
│          │                   │                       │                      │
│          │            Convierte XML           Decide qué acción             │
│          │            a JSON simple           ejecutar                      │
│          │                   │                       │                      │
│          ▼                   │                       ▼                      │
│   ┌──────────────┐           │            ┌──────────────────────┐         │
│   │              │           │            │                      │         │
│   │    Appium    │◀──────────┴────────────│    Agent Tools       │         │
│   │   (Driver)   │                        │   (click, type...)   │         │
│   └──────────────┘                        └──────────────────────┘         │
│          │                                                                  │
│          ▼                                                                  │
│   ┌──────────────┐                                                         │
│   │   Android    │                                                         │
│   │  (Emulador   │                                                         │
│   │  o Celular)  │                                                         │
│   └──────────────┘                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Descripción de cada componente

| Componente | Archivo | Función |
|------------|---------|---------|
| **Test Runner** | `src/test_runner.py` | Orquesta la ejecución de pruebas. Recibe un plan en lenguaje natural y coordina los demás módulos. |
| **UIParser** | `src/ui_parser.py` | Convierte el XML complejo de Android en JSON simple. Asigna IDs temporales a cada elemento. |
| **AI Orchestrator** | `src/ai_orchestrator.py` | Se comunica con GPT-4 o Claude. Envía la pantalla y recibe qué acción ejecutar. |
| **Agent Tools** | `src/agent_tools.py` | Ejecuta las acciones físicas: tocar, escribir, scroll, verificar texto. |
| **Config** | `src/config.py` | Gestiona la configuración: API keys, dispositivo, timeouts. |

## Estructura del Proyecto

```
qa_movil_agent/
├── src/                    # Código principal
│   ├── ui_parser.py       # Analiza pantallas Android
│   ├── agent_tools.py     # Ejecuta acciones (clic, escribir, etc.)
│   ├── ai_orchestrator.py # Comunicación con la IA
│   ├── test_runner.py     # Orquestador de pruebas
│   └── config.py          # Configuración
│
├── tests/                  # Pruebas automáticas
│   ├── conftest.py        # Configuración de pytest
│   ├── unit/              # Tests unitarios (test_*.py)
│   └── specs/             # Tests E2E (test_*.py y spec_*.py)
│       └── examples/      # Tests de usuario
│           └── test_example.py  # ✅ Ejemplos funcionales con AITestRunner
│
├── docs/                   # Esta documentación
├── reports/                # Reportes generados
└── scripts/                # Scripts útiles
```

## Soporte

Si tienes problemas o preguntas:

1. Revisa la sección de **Solución de Problemas** en cada guía
2. Verifica que todos los [Prerequisitos](05-prerequisites.md) estén instalados correctamente
3. Consulta el archivo [CLAUDE.md](../CLAUDE.md) para información técnica detallada
