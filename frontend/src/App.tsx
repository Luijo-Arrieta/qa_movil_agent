import React, { useState, useEffect } from 'react'
import TestEditor from './components/TestEditor'
import TestRunner from './components/TestRunner'
import ResultsViewer from './components/ResultsViewer'
import DeviceStatus from './components/DeviceStatus'
import './App.css'

function App() {
  const [activeTab, setActiveTab] = useState<'editor' | 'runner' | 'results' | 'devices'>('editor')
  const [testPlan, setTestPlan] = useState<string[]>([])
  const [testId, setTestId] = useState<string | null>(null)

  return (
    <div className="app">
      <header className="app-header">
        <h1>🤖 QA Mobile Agent</h1>
        <p>Agente de IA para pruebas móviles en Android</p>
      </header>

      <nav className="app-nav">
        <button
          className={activeTab === 'editor' ? 'active' : ''}
          onClick={() => setActiveTab('editor')}
        >
          📝 Editor
        </button>
        <button
          className={activeTab === 'runner' ? 'active' : ''}
          onClick={() => setActiveTab('runner')}
        >
          ▶️ Ejecutar
        </button>
        <button
          className={activeTab === 'results' ? 'active' : ''}
          onClick={() => setActiveTab('results')}
        >
          📊 Resultados
        </button>
        <button
          className={activeTab === 'devices' ? 'active' : ''}
          onClick={() => setActiveTab('devices')}
        >
          📱 Dispositivos
        </button>
      </nav>

      <main className="app-main">
        {activeTab === 'editor' && (
          <TestEditor
            testPlan={testPlan}
            onTestPlanChange={setTestPlan}
          />
        )}
        {activeTab === 'runner' && (
          <TestRunner
            testPlan={testPlan}
            onTestStart={(id) => {
              setTestId(id)
              setActiveTab('results')
            }}
          />
        )}
        {activeTab === 'results' && (
          <ResultsViewer testId={testId} />
        )}
        {activeTab === 'devices' && (
          <DeviceStatus />
        )}
      </main>
    </div>
  )
}

export default App
