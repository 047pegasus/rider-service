import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const orderAPI = {
  create: async (orderData) => {
    try {
      const response = await apiClient.post('/orders/', orderData)
      return response.data
    } catch (error) {
      // Re-throw with better error message
      if (error.response) {
        throw new Error(JSON.stringify(error.response.data))
      }
      throw error
    }
  },
  
  get: async (orderId) => {
    try {
      const response = await apiClient.get(`/orders/${orderId}/`)
      return response.data
    } catch (error) {
      if (error.response) {
        throw new Error(error.response.data.error || error.response.data.detail || 'Order not found')
      }
      throw error
    }
  },
  
  track: async (orderId) => {
    try {
      const response = await apiClient.get(`/orders/${orderId}/track/`)
      return response.data
    } catch (error) {
      if (error.response) {
        throw new Error(error.response.data.error || error.response.data.detail || 'Failed to track order')
      }
      throw error
    }
  },
  
  list: async () => {
    try {
      const response = await apiClient.get('/orders/')
      return response.data
    } catch (error) {
      if (error.response) {
        throw new Error(error.response.data.error || error.response.data.detail || 'Failed to list orders')
      }
      throw error
    }
  },

  completePayment: async (orderId) => {
    try {
      const response = await apiClient.post(`/orders/${orderId}/complete_payment/`)
      return response.data
    } catch (error) {
      if (error.response) {
        throw new Error(error.response.data.detail || error.response.data.error || 'Failed to complete payment')
      }
      throw error
    }
  },
}

export const deliveryAPI = {
  assign: async (orderId) => {
    try {
      const response = await apiClient.post('/deliveries/assign/', {
        order_id: orderId
      })
      return response.data
    } catch (error) {
      if (error.response) {
        throw new Error(error.response.data.detail || error.response.data.error || 'Failed to assign delivery')
      }
      throw error
    }
  },
  
  accept: async (deliveryId) => {
    try {
      const response = await apiClient.post(`/deliveries/${deliveryId}/accept/`)
      return response.data
    } catch (error) {
      if (error.response) {
        throw new Error(error.response.data.detail || error.response.data.error || 'Failed to accept delivery')
      }
      throw error
    }
  },

  deny: async (deliveryId) => {
    try {
      const response = await apiClient.post(`/deliveries/${deliveryId}/deny/`)
      return response.data
    } catch (error) {
      if (error.response) {
        throw new Error(error.response.data.detail || error.response.data.error || 'Failed to deny delivery')
      }
      throw error
    }
  },
  
  updateStatus: async (deliveryId, status, location, routeIndex, simulationStatus) => {
    try {
      const response = await apiClient.put(`/deliveries/${deliveryId}/update_status/`, {
        status,
        location,
        route_index: routeIndex,
        simulation_status: simulationStatus
      })
      return response.data
    } catch (error) {
      if (error.response) {
        throw new Error(error.response.data.detail || error.response.data.error || 'Failed to update delivery status')
      }
      throw error
    }
  },
  
  getState: async (deliveryId) => {
    try {
      const response = await apiClient.get(`/deliveries/${deliveryId}/state/`)
      return response.data
    } catch (error) {
      if (error.response) {
        throw new Error(error.response.data.detail || error.response.data.error || 'Failed to get delivery state')
      }
      throw error
    }
  },
}

export const riderAPI = {
  list: async () => {
    try {
      const response = await apiClient.get('/riders/')
      return response.data
    } catch (error) {
      if (error.response) {
        throw new Error(error.response.data.error || error.response.data.detail || 'Failed to list riders')
      }
      throw error
    }
  },
  
  getLocation: async (riderId) => {
    try {
      const response = await apiClient.get(`/riders/${riderId}/current_location/`)
      return response.data
    } catch (error) {
      if (error.response) {
        throw new Error(error.response.data.error || error.response.data.detail || 'Failed to get rider location')
      }
      throw error
    }
  },
  
  updateLocation: async (riderId, locationData) => {
    try {
      const response = await apiClient.put(`/riders/${riderId}/update_location/`, locationData)
      return response.data
    } catch (error) {
      if (error.response) {
        throw new Error(error.response.data.error || error.response.data.detail || 'Failed to update location')
      }
      throw error
    }
  },
  
  getActiveDeliveries: async (riderId) => {
    try {
      const response = await apiClient.get(`/riders/${riderId}/active_deliveries/`)
      return response.data
    } catch (error) {
      if (error.response) {
        throw new Error(error.response.data.error || error.response.data.detail || 'Failed to get active deliveries')
      }
      throw error
    }
  },
}

export default apiClient
