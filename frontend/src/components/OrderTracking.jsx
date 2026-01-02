import React, { useState, useEffect, useRef } from 'react'
import { MapContainer, TileLayer, Marker, Polyline, Popup } from 'react-leaflet'
import L from 'leaflet'
import { orderAPI } from '../api/client'
import ReconnectingWebSocket from 'reconnecting-websocket'
import './OrderTracking.css'

// Create custom bike icon
const bikeIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
})

// Alternative: Use a bike emoji or SVG
const createBikeIcon = () => {
  return L.divIcon({
    className: 'bike-marker',
    html: '<div style="font-size: 30px; transform: rotate(0deg);">🚴</div>',
    iconSize: [30, 30],
    iconAnchor: [15, 15]
  })
}

function OrderTracking({ orderId: initialOrderId }) {
  const [orderId, setOrderId] = useState(initialOrderId || '')
  const [order, setOrder] = useState(null)
  const [riderLocation, setRiderLocation] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [wsConnected, setWsConnected] = useState(false)
  const wsRef = useRef(null)

  useEffect(() => {
    if (orderId) {
      fetchOrderData()
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [orderId])

  // Connect WebSocket after order data is fetched (when we have UUID)
  useEffect(() => {
    if (order?.order_id) {
      connectWebSocket()
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [order?.order_id])

  const fetchOrderData = async () => {
    if (!orderId) return
    
    setLoading(true)
    setError(null)
    
    try {
      // orderId can be either UUID or order_number
      const trackingInfo = await orderAPI.track(orderId)
      setOrder(trackingInfo)
      if (trackingInfo.current_location) {
        setRiderLocation(trackingInfo.current_location)
      }
      // Update orderId to the actual UUID if we searched by order_number
      if (trackingInfo.order_id && trackingInfo.order_id !== orderId) {
        setOrderId(trackingInfo.order_id)
      }
    } catch (err) {
      const errorMsg = err.response?.data?.error || err.response?.data?.detail || err.message || 'Failed to fetch order data'
      setError(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  const connectWebSocket = () => {
    if (!orderId) return

    // Use order_id from order data if available (UUID), otherwise use orderId
    const wsOrderId = order?.order_id || orderId
    // Only connect if we have a UUID (WebSocket requires UUID)
    if (!wsOrderId || wsOrderId.length < 30) {
      return
    }

    const wsUrl = `ws://localhost:8000/ws/orders/${wsOrderId}/`
    const ws = new ReconnectingWebSocket(wsUrl)
    
    ws.onopen = () => {
      setWsConnected(true)
      console.log('WebSocket connected')
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        if (data.type === 'rider_assigned') {
          setOrder(prev => ({
            ...prev,
            rider: data.data.rider,
            status: 'assigned'
          }))
        } else if (data.type === 'location_update') {
          if (data.data.location) {
            setRiderLocation(data.data.location)
          }
        } else if (data.type === 'order_status') {
          setOrder(data.data)
          if (data.data.current_location) {
            setRiderLocation(data.data.current_location)
          }
        } else if (data.type === 'order_update') {
          setOrder(prev => ({
            ...prev,
            status: data.data.order_status || data.data.status || prev.status
          }))
          // Refresh order data to get updated information
          setTimeout(() => {
            fetchOrderData()
          }, 500)
        }
      } catch (err) {
        console.error('Error parsing WebSocket message:', err)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      setWsConnected(false)
    }

    ws.onclose = () => {
      setWsConnected(false)
      console.log('WebSocket disconnected')
    }

    wsRef.current = ws
  }

  const handleSearch = (e) => {
    e.preventDefault()
    if (orderId) {
      fetchOrderData()
      if (wsRef.current) {
        wsRef.current.close()
      }
      connectWebSocket()
    }
  }

  if (!orderId && !initialOrderId) {
    return (
      <div className="order-tracking">
        <div className="search-section">
          <h2>Track Your Order</h2>
          <form onSubmit={handleSearch} className="search-form">
            <input
              type="text"
              placeholder="Enter Order ID"
              value={orderId}
              onChange={(e) => setOrderId(e.target.value)}
              required
            />
            <button type="submit">Track</button>
          </form>
        </div>
      </div>
    )
  }

  const center = order?.current_location
    ? [order.current_location.lat, order.current_location.lng]
    : order?.pickup_lat
    ? [parseFloat(order.pickup_lat), parseFloat(order.pickup_lng)]
    : [28.6139, 77.2090]

  const route = []
  if (order?.pickup_lat && order?.pickup_lng) {
    route.push([parseFloat(order.pickup_lat), parseFloat(order.pickup_lng)])
  }
  if (riderLocation?.lat && riderLocation?.lng) {
    route.push([riderLocation.lat, riderLocation.lng])
  }
  if (order?.delivery_lat && order?.delivery_lng) {
    route.push([parseFloat(order.delivery_lat), parseFloat(order.delivery_lng)])
  }

  return (
    <div className="order-tracking">
      <div className="search-section">
        <form onSubmit={handleSearch} className="search-form">
          <input
            type="text"
            placeholder="Enter Order ID"
            value={orderId}
            onChange={(e) => setOrderId(e.target.value)}
            required
          />
          <button type="submit">Track</button>
        </form>
        <div className={`ws-status ${wsConnected ? 'connected' : 'disconnected'}`}>
          {wsConnected ? '🟢 Live' : '🔴 Offline'}
        </div>
      </div>

      {loading && <div className="loading">Loading order data...</div>}
      {error && <div className="alert alert-error">{error}</div>}

      {order && (
        <>
          <div className="order-info">
            <div className="info-card">
              <h3>Order Information</h3>
              <p><strong>Order Number:</strong> {order.order_number}</p>
              <p><strong>Status:</strong> <span className={`status status-${order.status}`}>{order.status}</span></p>
              {order.rider && (
                <>
                  <p><strong>Rider:</strong> {order.rider.name}</p>
                  <p><strong>Rider Phone:</strong> {order.rider.phone}</p>
                </>
              )}
            </div>
            <div className="info-card">
              <h3>Locations</h3>
              <p><strong>Pickup:</strong> {order.pickup_address || order.pickup_location?.address || 'N/A'}</p>
              <p><strong>Delivery:</strong> {order.delivery_address || order.delivery_location?.address || 'N/A'}</p>
            </div>
          </div>

          <div className="map-section">
            <h3>Live Tracking Map</h3>
            <MapContainer
              center={center}
              zoom={13}
              style={{ height: '500px', width: '100%' }}
              key={JSON.stringify(center)}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              
              {order.pickup_lat && order.pickup_lng && (
                <Marker position={[parseFloat(order.pickup_lat), parseFloat(order.pickup_lng)]}>
                  <Popup>
                    <strong>Pickup Location</strong><br />
                    {order.pickup_address}
                  </Popup>
                </Marker>
              )}

              {riderLocation?.lat && riderLocation?.lng && (
                <Marker 
                  position={[riderLocation.lat, riderLocation.lng]}
                  icon={createBikeIcon()}
                >
                  <Popup>
                    <strong>Rider Location</strong><br />
                    {order.rider?.name || 'Rider'}<br />
                    Speed: {riderLocation.speed ? `${riderLocation.speed} km/h` : 'N/A'}
                  </Popup>
                </Marker>
              )}

              {order.delivery_lat && order.delivery_lng && (
                <Marker position={[parseFloat(order.delivery_lat), parseFloat(order.delivery_lng)]}>
                  <Popup>
                    <strong>Delivery Location</strong><br />
                    {order.delivery_address}
                  </Popup>
                </Marker>
              )}

              {route.length > 1 && (
                <Polyline positions={route} color="blue" dashArray="10, 10" />
              )}
            </MapContainer>
          </div>
        </>
      )}
    </div>
  )
}

export default OrderTracking
