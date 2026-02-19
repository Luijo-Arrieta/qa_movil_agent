import React, { useState } from 'react'
import { testApi, TestPlanRequest } from '../services/api'
import './TestRunner.css'

interface TestRunnerProps {
  testPlan: string[]
  onTestStart: (testId: string) => void
}

const TestRunner: React.FC<TestRunnerProps> = ({ testPlan, onTestStart }) => {
  const [objective, setObjective] = useState('')
  const [deviceName, setDeviceName] = useState('')
  const [appPackage, setAppPackage] = useState('')
  const [running, setRunning] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  const handleRun = async () => {
    if (testPlan.length === 0) {
      setMessage({ type: 'error', text: 'Por favor define los pasos del test en el Editor' })
      return
    }

    setRunning(true)
    setMessage(null)

    try {
      const request: TestPlanRequest = {
        test_plan: testPlan,
        objective: objective || undefined,
        device_name: deviceName || undefined,
        app_package: appPackage || undefined,
      }

      const response = await testApi.executeTest(request)
      setMessage({ type: 'success', text: `Test iniciado: ${response.test_id}` })
      onTestStart(response.test_id)
    } catch (error: any) {
      setMessage({ type: 'error', text: error.response?.data?.detail || 'Error ejecutando test' })
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="card">
      <h2>▶️ Ejecutar Test</h2>
      
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
        <label>Dispositivo (opcional)</label>
        <input
          type="text"
          value={deviceName}
          onChange={(e) => setDeviceName(e.target.value)}
          placeholder="Ej: emulator-5554"
        />
      </div>

      <div className="form-group">
        <label>App Package (opcional)</label>
        <input
          type="text"
          value={appPackage}
          onChange={(e) => setAppPackage(e.target.value)}
          placeholder="Ej: com.example.app"
        />
      </div>

      <div className="test-runner-info">
        <p>
          <strong>Pasos a ejecutar:</strong> {testPlan.length}
        </p>
        {testPlan.length > 0 && (
          <ul>
            {testPlan.map((step, idx) => (
              <li key={idx}>{step}</li>
            ))}
          </ul>
        )}
        {testPlan.length === 0 && (
          <p className="warning">⚠️ Ve al Editor para definir los pasos del test</p>
        )}
      </div>

      <button
        className="btn btn-success"
        onClick={handleRun}
        disabled={running || testPlan.length === 0}
      >
        {running ? 'Ejecutando...' : '▶️ Ejecutar Test'}
      </button>
    </div>
  )
}

export default TestRunner
