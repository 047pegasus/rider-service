import React, { useState, useEffect, useRef } from 'react'
import { MapContainer, TileLayer, Marker, Polyline, Popup } from 'react-leaflet'
import { useMap } from 'react-leaflet'
import { riderAPI, deliveryAPI } from '../api/client'
import { routingAPI } from '../api/routing'
import ReconnectingWebSocket from 'reconnecting-websocket'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select'
import { useApp } from '../context/AppContext'

// Smooth marker animation component
function AnimatedMarker({ position, children }) {
  const map = useMap()
  const markerRef = useRef(null)

  useEffect(() => {
    if (markerRef.current && position) {
      markerRef.current.setLatLng([position.lat, position.lng])
      map.setView([position.lat, position.lng], map.getZoom(), { animate: true, duration: 0.5 })
    }
  }, [position, map])

  return <Marker ref={markerRef} position={[position?.lat || 0, position?.lng || 0]}>{children}</Marker>
}

function RiderDeviceNew() {
  const { activeRider, setActiveRider } = useApp()
  const [riders, setRiders] = useState([])
  const [activeDeliveries, setActiveDeliveries] = useState([])
  const [currentDelivery, setCurrentDelivery] = useState(null)
  const [currentLocation, setCurrentLocation] = useState(null)
  const [routePoints, setRoutePoints] = useState([])
  const [currentRouteIndex, setCurrentRouteIndex] = useState(0)
  const [isSimulating, setIsSimulating] = useState(false)
  const [wsConnected, setWsConnected] = useState(false)
  const [mapCenter, setMapCenter] = useState([28.6139, 77.2090])
  
  const wsRef = useRef(null)
  const simulationRef = useRef(null)
  const statusRef = useRef('idle')

  useEffect(() => {
    fetchRiders()
  }, [])

  useEffect(() => {
    if (activeRider) {
      fetchActiveDeliveries()
      fetchCurrentLocation()
      connectWebSocket()
    }
    return () => {
      if (wsRef.current) wsRef.current.close()
    }
  }, [activeRider])

  useEffect(() => {
    // Auto-accept and start simulation when delivery is assigned
    if (activeDeliveries.length > 0 && !currentDelivery) {
      const assigned = activeDeliveries.find(d => d.status === 'assigned')
      if (assigned) {
        handleAcceptDelivery(assigned)
      } else {
        setCurrentDelivery(activeDeliveries[0])
      }
    }
  }, [activeDeliveries])

  useEffect(() => {
    if (currentDelivery && currentLocation) {
      setupRoute()
    }
  }, [currentDelivery, currentLocation])

  const fetchRiders = async () => {
    try {
      const data = await riderAPI.list()
      setRiders(data)
      if (data.length > 0 && !activeRider) {
        setActiveRider(data[0])
      }
    } catch (err) {
      console.error('Failed to fetch riders:', err)
    }
  }

  const fetchActiveDeliveries = async () => {
    if (!activeRider) return
    try {
      const data = await riderAPI.getActiveDeliveries(activeRider.id)
      setActiveDeliveries(data)
    } catch (err) {
      console.error('Failed to fetch deliveries:', err)
    }
  }

  const fetchCurrentLocation = async () => {
    if (!activeRider) return
    try {
      const location = await riderAPI.getLocation(activeRider.id)
      if (location && location.lat) {
        setCurrentLocation({ lat: location.lat, lng: location.lng })
        setMapCenter([location.lat, location.lng])
      }
    } catch (err) {
      console.error('Failed to fetch location:', err)
    }
  }

  const connectWebSocket = () => {
    if (!activeRider) return

    const wsUrl = `ws://localhost:8000/ws/riders/${activeRider.id}/`
    const ws = new ReconnectingWebSocket(wsUrl)
    
    ws.onopen = () => {
      setWsConnected(true)
      console.log('Rider WebSocket connected')
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'delivery_assigned') {
          fetchActiveDeliveries()
        }
      } catch (err) {
        console.error('WebSocket message error:', err)
      }
    }

    ws.onerror = () => setWsConnected(false)
    ws.onclose = () => setWsConnected(false)

    wsRef.current = ws
  }

  const handleAcceptDelivery = async (delivery) => {
    try {
      await deliveryAPI.accept(delivery.delivery_id)
      setCurrentDelivery(delivery)
      statusRef.current = 'accepted'
      fetchActiveDeliveries()
      // Auto-start simulation after acceptance
      setTimeout(() => {
        startSimulation(delivery)
      }, 1000)
    } catch (err) {
      console.error('Failed to accept delivery:', err)
    }
  }

  const setupRoute = async () => {
    if (!currentDelivery || !currentLocation) return

    const pickup = currentDelivery.pickup_location
    const delivery = currentDelivery.delivery_location

    if (!pickup?.lat || !delivery?.lat) return

    try {
      // Use routing service for accurate route
      const route1 = await routingAPI.calculateRoute(
        currentLocation,
        { lat: pickup.lat, lng: pickup.lng }
      )
      const route2 = await routingAPI.calculateRoute(
        { lat: pickup.lat, lng: pickup.lng },
        { lat: delivery.lat, lng: delivery.lng }
      )
      
      setRoutePoints([...route1, ...route2])
      setCurrentRouteIndex(0)
    } catch (err) {
      console.error('Route calculation error:', err)
      // Fallback to direct route
      const route1 = calculateDirectRoute(currentLocation, { lat: pickup.lat, lng: pickup.lng })
      const route2 = calculateDirectRoute({ lat: pickup.lat, lng: pickup.lng }, { lat: delivery.lat, lng: delivery.lng })
      setRoutePoints([...route1, ...route2])
    }
  }

  const calculateDirectRoute = (start, end, numPoints = 50) => {
    const points = []
    for (let i = 0; i <= numPoints; i++) {
      const ratio = i / numPoints
      points.push({
        lat: start.lat + (end.lat - start.lat) * ratio,
        lng: start.lng + (end.lng - start.lng) * ratio
      })
    }
    return points
  }

  const sendLocationViaWebSocket = (location, deliveryId) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'location_update',
        data: {
          lat: location.lat,
          lng: location.lng,
          accuracy: 10.0,
          speed: 40.0,
          heading: 0,
          battery_level: 85,
          delivery_id: deliveryId
        }
      }))
    }
  }

  const startSimulation = (delivery) => {
    if (!delivery || routePoints.length === 0) return

    setIsSimulating(true)
    statusRef.current = 'going_to_pickup'
    setCurrentRouteIndex(0)

    const pickupIndex = Math.floor(routePoints.length / 2)
    let currentIndex = 0
    let pickupReached = false

    simulationRef.current = setInterval(() => {
      if (statusRef.current === 'at_pickup') return

      currentIndex += 1

      // Reached pickup
      if (statusRef.current === 'going_to_pickup' && currentIndex >= pickupIndex && !pickupReached) {
        statusRef.current = 'at_pickup'
        pickupReached = true
        setCurrentRouteIndex(pickupIndex)
        
        deliveryAPI.updateStatus(delivery.delivery_id, 'in_progress', routePoints[pickupIndex])
          .then(() => {
            setTimeout(() => {
              statusRef.current = 'going_to_delivery'
            }, 3000) // Wait 3 seconds at pickup
          })

        return
      }

      // Reached delivery
      if (statusRef.current === 'going_to_delivery' && currentIndex >= routePoints.length) {
        statusRef.current = 'completed'
        setCurrentRouteIndex(routePoints.length - 1)
        deliveryAPI.updateStatus(delivery.delivery_id, 'completed', routePoints[routePoints.length - 1])
        stopSimulation()
        return
      }

      if (currentIndex < routePoints.length) {
        const point = routePoints[currentIndex]
        sendLocationViaWebSocket(point, delivery.delivery_id)
        setCurrentLocation(point)
        setCurrentRouteIndex(currentIndex)
        // Smooth map center update
        setMapCenter([point.lat, point.lng])
      }
    }, 2000) // Update every 2 seconds
  }

  const stopSimulation = () => {
    if (simulationRef.current) {
      clearInterval(simulationRef.current)
      simulationRef.current = null
    }
    setIsSimulating(false)
  }

  const displayedRoute = routePoints.slice(0, currentRouteIndex + 1)
  const remainingRoute = routePoints.slice(currentRouteIndex + 1)

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Rider Device</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4">
            <Select
              value={activeRider?.id || ''}
              onValueChange={(value) => {
                const rider = riders.find(r => r.id === value)
                setActiveRider(rider)
              }}
            >
              <SelectTrigger className="w-[300px]">
                <SelectValue placeholder="Select Rider" />
              </SelectTrigger>
              <SelectContent>
                {riders.map(rider => (
                  <SelectItem key={rider.id} value={rider.id}>
                    {rider.name} ({rider.phone})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <div className={`px-3 py-1 rounded-full text-sm ${wsConnected ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
              {wsConnected ? '🟢 Connected' : '🔴 Disconnected'}
            </div>
          </div>

          {activeDeliveries.length > 0 && (
            <div>
              <h3 className="text-sm font-medium mb-2">Active Deliveries</h3>
              {activeDeliveries.map(delivery => (
                <Card key={delivery.delivery_id} className="mb-2">
                  <CardContent className="p-4">
                    <div className="flex justify-between items-center">
                      <div>
                        <p className="font-medium">{delivery.order_number}</p>
                        <p className="text-sm text-muted-foreground">Status: {delivery.status}</p>
                      </div>
                      {delivery.status === 'assigned' && (
                        <Button onClick={() => handleAcceptDelivery(delivery)}>
                          Accept
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {currentDelivery && (
            <div className="text-sm">
              <p><strong>Current Delivery:</strong> {currentDelivery.order_number}</p>
              <p><strong>Status:</strong> {statusRef.current}</p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Rider Location Map</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[600px] rounded-md overflow-hidden">
            <MapContainer
              center={mapCenter}
              zoom={13}
              style={{ height: '100%', width: '100%' }}
              zoomControl={true}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />

              {currentLocation && (
                <AnimatedMarker position={currentLocation}>
                  <Popup>
                    <strong>Rider Location</strong><br />
                    {activeRider?.name || 'Rider'}
                  </Popup>
                </AnimatedMarker>
              )}

              {currentDelivery?.pickup_location?.lat && (
                <Marker position={[currentDelivery.pickup_location.lat, currentDelivery.pickup_location.lng]}>
                  <Popup>Pickup Location</Popup>
                </Marker>
              )}

              {currentDelivery?.delivery_location?.lat && (
                <Marker position={[currentDelivery.delivery_location.lat, currentDelivery.delivery_location.lng]}>
                  <Popup>Delivery Location</Popup>
                </Marker>
              )}

              {displayedRoute.length > 1 && (
                <Polyline positions={displayedRoute.map(p => [p.lat, p.lng])} color="blue" weight={4} />
              )}

              {remainingRoute.length > 1 && (
                <Polyline positions={remainingRoute.map(p => [p.lat, p.lng])} color="gray" weight={2} dashArray="5, 5" />
              )}
            </MapContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default RiderDeviceNew
