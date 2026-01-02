import React, { createContext, useContext, useState, useCallback } from 'react'

const AppContext = createContext()

export function AppProvider({ children }) {
  const [orders, setOrders] = useState({})
  const [activeRider, setActiveRider] = useState(null)
  const [trackingOrderId, setTrackingOrderId] = useState(null)

  const addOrder = useCallback((orderId, orderData) => {
    setOrders(prev => ({
      ...prev,
      [orderId]: orderData
    }))
  })

  const updateOrder = useCallback((orderId, updates) => {
    setOrders(prev => ({
      ...prev,
      [orderId]: {
        ...prev[orderId],
        ...updates
      }
    }))
  })

  return (
    <AppContext.Provider
      value={{
        orders,
        addOrder,
        updateOrder,
        activeRider,
        setActiveRider,
        trackingOrderId,
        setTrackingOrderId,
      }}
    >
      {children}
    </AppContext.Provider>
  )
}

export function useApp() {
  const context = useContext(AppContext)
  if (!context) {
    throw new Error('useApp must be used within AppProvider')
  }
  return context
}
