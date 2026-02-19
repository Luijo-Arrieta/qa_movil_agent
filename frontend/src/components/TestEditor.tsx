import React, { useState, useEffect } from 'react'
import { testApi } from '../services/api'
import './TestEditor.css'

interface TestEditorProps {
  testPlan: string[]
  onTestPlanChange: (plan: string[]) => void
}

const TestEditor: React.FC<TestEditorProps> = ({ testPlan, onTestPlanChange }) => {
  const [objective, setObjective] = useState('')
  const [stepsText, setStepsText] = useState('')
  const [generating, setGenerating] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  useEffect(() => {
    // Cargar test plan actual
    setStepsText(testPlan.join('\n'))
  }, [testPlan])

  const handleStepsChange = (text: string) => {
    setStepsText(text)
    const steps = text.split('\n').filter(step => step.trim())
    onTestPlanChange(steps)
  }

  const handleGenerate = async () => {
    if (!objective.trim()) {
      setMessage({ type: 'error', text: 'Por favor ingresa un objetivo para el test' })
      return
    }

    setGenerating(true)
    setMessage(null)

    try {
      await testApi.generateTest(objective)
      setMessage({ type: 'success', text: 'Archivo de test generado exitosamente' })
    } catch (error: any) {
      setMessage({ type: 'error', text: error.response?.data?.detail || 'Error generando test' })
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="card">
      <h2>📝 Editor de Test Plan</h2>
      
      {message && (
        <div className={message.type}>
          {message.text}
        </div>
      )}

      <div className="form-group">
        <label>Objetivo del Test (opcional)</label>
        <input
          type="text"
          value={objective}
          onChange={(e) => setObjective(e.target.value)}
          placeholder="Ej: Realizar login en la aplicación"
        />
      </div>

      <div className="form-group">
        <label>Pasos del Test (uno por línea)</label>
        <textarea
          value={stepsText}
          onChange={(e) => handleStepsChange(e.target.value)}
          placeholder="Ingresar usuario 'test@example.com'&#10;Ingresar password '123456'&#10;Tocar botón Ingresar&#10;Verificar que se inició la sesión"
        />
      </div>

      <div className="test-editor-actions">
        <button
          className="btn btn-primary"
          onClick={handleGenerate}
          disabled={generating || !objective.trim()}
        >
          {generating ? 'Generando...' : 'Generar Archivo de Test'}
        </button>
        <div className="test-plan-info">
          {testPlan.length > 0 && (
            <span>{testPlan.length} paso(s) definido(s)</span>
          )}
        </div>
      </div>
    </div>
  )
}

export default TestEditor
