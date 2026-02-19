import React, { useState, useEffect } from 'react'
import { deviceApi, DeviceInfo } from '../services/api'
import './DeviceStatus.css'

const DeviceStatus: React.FC = () => {
  const [devices, setDevices] = useState<DeviceInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchDevices()
  }, [])

  const fetchDevices = async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await deviceApi.listDevices()
      setDevices(data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error obteniendo dispositivos')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card">
      <div className="device-status-header">
        <h2>📱 Dispositivos Android</h2>
        <button className="btn btn-secondary" onClick={fetchDevices}>
          🔄 Actualizar
        </button>
      </div>

      {loading && (
        <div className="loading">Cargando dispositivos...</div>
      )}

      {error && (
        <div className="error">{error}</div>
      )}

      {!loading && !error && devices.length === 0 && (
        <div className="no-devices">
          <p>⚠️ No hay dispositivos conectados</p>
          <p className="hint">
            Conecta un dispositivo Android o inicia un emulador y actualiza la lista.
          </p>
        </div>
      )}

      {!loading && !error && devices.length > 0 && (
        <div className="devices-list">
          {devices.map((device) => (
            <div key={device.device_id} className="device-card">
              <div className="device-info">
                <div className="device-name">{device.device_name}</div>
                <div className="device-id">{device.device_id}</div>
              </div>
              <span className={`status-badge status-${device.status}`}>
                {device.status}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default DeviceStatus
