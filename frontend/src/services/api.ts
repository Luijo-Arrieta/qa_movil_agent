import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface TestPlanRequest {
  test_plan: string[]
  objective?: string
  device_name?: string
  app_package?: string
  app_activity?: string
}

export interface TestExecutionResponse {
  test_id: string
  status: string
  message: string
}

export interface TestResult {
  test_id: string
  status: string
  success: boolean
  total_steps: number
  completed_steps: number
  failed_steps: number
  execution_time: number
  error_message?: string
  execution_stats?: any
}

export interface DeviceInfo {
  device_id: string
  device_name: string
  status: string
  platform: string
  version?: string
}

export const testApi = {
  executeTest: async (request: TestPlanRequest): Promise<TestExecutionResponse> => {
    const response = await api.post('/api/v1/tests/execute', request)
    return response.data
  },

  getResult: async (testId: string): Promise<TestResult> => {
    const response = await api.get(`/api/v1/results/${testId}`)
    return response.data
  },

  generateTest: async (description: string, testName?: string): Promise<any> => {
    const response = await api.post('/api/v1/tests/generate', {
      description,
      test_name: testName,
    })
    return response.data
  },
}

export const deviceApi = {
  listDevices: async (): Promise<DeviceInfo[]> => {
    const response = await api.get('/api/v1/devices')
    return response.data
  },
}

export default api
