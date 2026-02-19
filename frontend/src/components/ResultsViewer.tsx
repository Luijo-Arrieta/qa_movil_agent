import React, { useState, useEffect } from 'react'
import { testApi, TestResult } from '../services/api'
import './ResultsViewer.css'

interface ResultsViewerProps {
  testId: string | null
}

const ResultsViewer: React.FC<ResultsViewerProps> = ({ testId }) => {
  const [result, setResult] = useState<TestResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!testId) return

    const fetchResult = async () => {
      setLoading(true)
      setError(null)

      try {
        const data = await testApi.getResult(testId)
        setResult(data)

        // Si el test sigue corriendo, volver a consultar en 2 segundos
        if (data.status === 'running') {
          setTimeout(() => {
            fetchResult()
          }, 2000)
        }
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Error obteniendo resultado')
      } finally {
        setLoading(false)
      }
    }

    fetchResult()
  }, [testId])

  if (!testId) {
    return (
      <div className="card">
        <h2>📊 Resultados</h2>
        <p>No hay ningún test seleccionado. Ejecuta un test para ver los resultados.</p>
      </div>
    )
  }

  if (loading && !result) {
    return (
      <div className="card">
        <h2>📊 Resultados</h2>
        <div className="loading">Cargando...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card">
        <h2>📊 Resultados</h2>
        <div className="error">{error}</div>
      </div>
    )
  }

  if (!result) {
    return (
      <div className="card">
        <h2>📊 Resultados</h2>
        <div className="error">No se encontró el resultado del test</div>
      </div>
    )
  }

  return (
    <div className="card">
      <h2>📊 Resultados del Test</h2>
      
      <div className="result-header">
        <div>
          <strong>Test ID:</strong> {result.test_id}
        </div>
        <span className={`status-badge status-${result.status}`}>
          {result.status}
        </span>
      </div>

      <div className="result-stats">
        <div className="stat">
          <div className="stat-label">Estado</div>
          <div className={`stat-value status-${result.status}`}>
            {result.success ? '✅ Exitoso' : '❌ Falló'}
          </div>
        </div>
        <div className="stat">
          <div className="stat-label">Pasos Completados</div>
          <div className="stat-value">{result.completed_steps} / {result.total_steps}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Pasos Fallidos</div>
          <div className="stat-value">{result.failed_steps}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Tiempo de Ejecución</div>
          <div className="stat-value">{result.execution_time.toFixed(2)}s</div>
        </div>
      </div>

      {result.error_message && (
        <div className="error">
          <strong>Error:</strong> {result.error_message}
        </div>
      )}

      {result.status === 'running' && (
        <div className="loading">
          ⏳ Test en ejecución... Recargando automáticamente...
        </div>
      )}
    </div>
  )
}

export default ResultsViewer
