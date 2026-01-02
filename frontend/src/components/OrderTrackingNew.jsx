import React, { useState, useEffect, useRef } from 'react'
import { MapContainer, TileLayer, Marker, Polyline, Popup } from 'react-leaflet'
import { useMap } from 'react-leaflet'
import L from 'leaflet'
import { orderAPI } from '../api/client'
import ReconnectingWebSocket from 'reconnecting-websocket'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Input } from './ui/input'
import { Button } from './ui/button'
import { useApp } from '../context/AppContext'

// Create bike icon
const createBikeIcon = () => {
  return L.divIcon({
    className: 'bike-marker',
    html: '<div style="font-size: 30px; transform: rotate(0deg);">🚴</div>',
    iconSize: [30, 30],
    iconAnchor: [15, 15]
  })
}

// Smooth animated marker
function AnimatedRiderMarker({ position, children }) {
  const map = useMap()
  const markerRef = useRef(null)

  useEffect(() => {
    if (markerRef.current && position) {
      markerRef.current.setLatLng([position.lat, position.lng])
      // Smoothly pan map to follow rider (without zoom change)
      map.panTo([position.lat, position.lng], { animate: true, duration: 1.0 })
    }
  }, [position, map])

  return (
    <Marker
      ref={markerRef}
      position={[position?.lat || 0, position?.lng || 0]}
      icon={createBikeIcon()}
    >
      {children}
    </Marker>
  )
}

function OrderTrackingNew({ orderId: initialOrderId }) {
  const { trackingOrderId, setTrackingOrderId, orders, updateOrder } = useApp()
  const [localOrderId, setLocalOrderId] = useState(trackingOrderId || initialOrderId || '')
  const orderId = trackingOrderId || initialOrderId || localOrderId || ''
  const [order, setOrder] = useState(null)
  const [riderLocation, setRiderLocation] = useState(null)
  const [routePoints, setRoutePoints] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [wsConnected, setWsConnected] = useState(false)
  const wsRef = useRef(null)
  const mapRef = useRef(null)

  useEffect(() => {
    if (orderId) {
      fetchOrderData()
      connectWebSocket()
    }
    return () => {
      if (wsRef.current) wsRef.current.close()
    }
  }, [orderId])

  const fetchOrderData = async () => {
    if (!orderId) return
    
    setLoading(true)
    setError(null)
    
    try {
      const trackingInfo = await orderAPI.track(orderId)
      setOrder(trackingInfo)
      updateOrder(orderId, trackingInfo)
      
      if (trackingInfo.current_location) {
        setRiderLocation(trackingInfo.current_location)
      }
      
      // Build route points if we have locations
      if (trackingInfo.pickup_lat && trackingInfo.delivery_lat) {
        buildRoute(trackingInfo)
      }
      
      if (trackingInfo.order_id && trackingInfo.order_id !== orderId) {
        setTrackingOrderId(trackingInfo.order_id)
      }
    } catch (err) {
      const errorMsg = err.response?.data?.error || err.response?.data?.detail || err.message || 'Failed to fetch order data'
      setError(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  const buildRoute = async (orderData) => {
    if (!orderData.pickup_lat || !orderData.delivery_lat) return

    try {
      const { routingAPI } = await import('../api/routing')
      const route = await routingAPI.calculateRoute(
        { lat: orderData.pickup_lat, lng: orderData.pickup_lng },
        { lat: orderData.delivery_lat, lng: orderData.delivery_lng }
      )
      setRoutePoints(route)
    } catch (err) {
      console.error('Route calculation error:', err)
      // Fallback to direct route
      const points = []
      for (let i = 0; i <= 50; i++) {
        const ratio = i / 50
        points.push({
          lat: orderData.pickup_lat + (orderData.delivery_lat - orderData.pickup_lat) * ratio,
          lng: orderData.pickup_lng + (orderData.delivery_lng - orderData.pickup_lng) * ratio
        })
      }
      setRoutePoints(points)
    }
  }

  const connectWebSocket = () => {
    if (!orderId) return

    const wsOrderId = order?.order_id || orderId
    if (!wsOrderId || wsOrderId.length < 30) return

    const wsUrl = `ws://localhost:8000/ws/orders/${wsOrderId}/`
    const ws = new ReconnectingWebSocket(wsUrl)
    
    ws.onopen = () => {
      setWsConnected(true)
      console.log('Order WebSocket connected')
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
          fetchOrderData() // Refresh to get full data
        } else if (data.type === 'location_update') {
          if (data.data.location) {
            setRiderLocation(data.data.location)
            // Update route with rider's current position
            if (order?.pickup_lat && order?.delivery_lat) {
              updateRouteWithRiderPosition(data.data.location)
            }
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
          setTimeout(() => fetchOrderData(), 500)
        }
      } catch (err) {
        console.error('Error parsing WebSocket message:', err)
      }
    }

    ws.onerror = () => setWsConnected(false)
    ws.onclose = () => setWsConnected(false)

    wsRef.current = ws
  }

  const updateRouteWithRiderPosition = (riderPos) => {
    // Route is already calculated, just update rider position marker
    // The route visualization will show rider's progress
  }

  const center = riderLocation
    ? [riderLocation.lat, riderLocation.lng]
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
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Track Your Order</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-2">
            <Input
              type="text"
              placeholder="Enter Order ID or Order Number"
              value={localOrderId}
              onChange={(e) => {
                setLocalOrderId(e.target.value)
                setTrackingOrderId(e.target.value)
              }}
              className="flex-1"
            />
            <Button onClick={() => {
              setTrackingOrderId(localOrderId)
              fetchOrderData()
            }}>Track</Button>
            <div className={`px-3 py-1 rounded-full text-sm ${wsConnected ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
              {wsConnected ? '🟢 Live' : '🔴 Offline'}
            </div>
          </div>

          {loading && <div className="text-center py-4">Loading order data...</div>}
          {error && <div className="bg-destructive/10 text-destructive p-3 rounded-md">{error}</div>}

          {order && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Order Information</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <p><strong>Order Number:</strong> {order.order_number}</p>
                    <p><strong>Status:</strong> <span className="px-2 py-1 rounded bg-primary/20 text-primary">{order.status}</span></p>
                    {order.rider && (
                      <>
                        <p><strong>Rider:</strong> {order.rider.name}</p>
                        <p><strong>Rider Phone:</strong> {order.rider.phone}</p>
                      </>
                    )}
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Locations</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <p><strong>Pickup:</strong> {order.pickup_address || 'N/A'}</p>
                    <p><strong>Delivery:</strong> {order.delivery_address || 'N/A'}</p>
                  </CardContent>
                </Card>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Live Tracking Map</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-[500px] rounded-md overflow-hidden">
                    <MapContainer
                      center={center}
                      zoom={13}
                      style={{ height: '100%', width: '100%' }}
                      zoomControl={true}
                      key={`map-${order?.order_id || orderId}`}
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
                        <AnimatedRiderMarker position={riderLocation}>
                          <Popup>
                            <strong>Rider Location</strong><br />
                            {order.rider?.name || 'Rider'}<br />
                            Speed: {riderLocation.speed ? `${riderLocation.speed} km/h` : 'N/A'}
                          </Popup>
                        </AnimatedRiderMarker>
                      )}

                      {order.delivery_lat && order.delivery_lng && (
                        <Marker position={[parseFloat(order.delivery_lat), parseFloat(order.delivery_lng)]}>
                          <Popup>
                            <strong>Delivery Location</strong><br />
                            {order.delivery_address}
                          </Popup>
                        </Marker>
                      )}

                      {routePoints.length > 1 && (
                        <Polyline 
                          positions={routePoints.map(p => [p.lat, p.lng])} 
                          color="blue" 
                          weight={3}
                          opacity={0.7}
                        />
                      )}

                      {/* Show route from pickup to rider to delivery */}
                      {riderLocation && order?.pickup_lat && order?.delivery_lat && (
                        <>
                          <Polyline 
                            positions={[
                              [parseFloat(order.pickup_lat), parseFloat(order.pickup_lng)],
                              [riderLocation.lat, riderLocation.lng]
                            ]} 
                            color="green" 
                            weight={2}
                            dashArray="5, 5"
                          />
                          {riderLocation.lat > parseFloat(order.pickup_lat) && (
                            <Polyline 
                              positions={[
                                [riderLocation.lat, riderLocation.lng],
                                [parseFloat(order.delivery_lat), parseFloat(order.delivery_lng)]
                              ]} 
                              color="orange" 
                              weight={2}
                              dashArray="5, 5"
                            />
                          )}
                        </>
                      )}
                    </MapContainer>
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default OrderTrackingNew
