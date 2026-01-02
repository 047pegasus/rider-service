import React, { useState, useEffect, useRef } from 'react'
import { MapContainer, TileLayer, Marker, Polyline, Popup } from 'react-leaflet'
import { useMap } from 'react-leaflet'
import L from 'leaflet'
import { riderAPI, deliveryAPI } from '../api/client'
import { routingAPI } from '../api/routing'
import ReconnectingWebSocket from 'reconnecting-websocket'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select'
import { useApp } from '../context/AppContext'
import { CheckCircle2, XCircle, Package, MapPin, Navigation } from 'lucide-react'

// Smooth marker animation component
function AnimatedMarker({ position, children }) {
  const map = useMap()
  const markerRef = useRef(null)

  useEffect(() => {
    if (markerRef.current && position) {
      markerRef.current.setLatLng([position.lat, position.lng])
      map.panTo([position.lat, position.lng], { animate: true, duration: 1.0 })
    }
  }, [position, map])

  const bikeIcon = L.divIcon({
    className: 'bike-marker',
    html: '<div style="font-size: 30px;">🚴</div>',
    iconSize: [30, 30],
    iconAnchor: [15, 15]
  })

  return (
    <Marker 
      ref={markerRef} 
      position={[position?.lat || 0, position?.lng || 0]}
      icon={bikeIcon}
    >
      {children}
    </Marker>
  )
}

function RiderDeviceImproved() {
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
      restoreDeliveryState() // Restore any active delivery state
    }
    return () => {
      if (wsRef.current) wsRef.current.close()
    }
  }, [activeRider])
  
  const restoreDeliveryState = async () => {
    if (!activeRider) return
    
    try {
      // Get active deliveries
      const deliveries = await riderAPI.getActiveDeliveries(activeRider.id)
      
      // Find accepted or in-progress delivery
      const activeDelivery = deliveries.find(d => 
        d.status === 'accepted' || d.status === 'in_progress' || d.status === 'collected'
      )
      
      if (activeDelivery) {
        // Get delivery state from backend
        const state = await deliveryAPI.getState(activeDelivery.delivery_id)
        
        if (state) {
          const restoredDelivery = {
            delivery_id: state.delivery_id,
            order_id: state.order.id,
            order_number: state.order.order_number,
            status: state.status,
            pickup_location: state.order.pickup_location,
            delivery_location: state.order.delivery_location
          }
          
          // Restore delivery
          setCurrentDelivery(restoredDelivery)
          
          // Restore location from delivery state or rider location
          let restoredLocation = null
          if (state.last_location?.lat) {
            restoredLocation = {
              lat: state.last_location.lat,
              lng: state.last_location.lng
            }
          } else {
            // Fallback to rider's current location
            const location = await riderAPI.getLocation(activeRider.id)
            if (location && location.lat) {
              restoredLocation = { lat: location.lat, lng: location.lng }
            }
          }
          
          if (restoredLocation) {
            setCurrentLocation(restoredLocation)
            setMapCenter([restoredLocation.lat, restoredLocation.lng])
          }
          
          // Restore simulation state
          if (state.simulation_status && state.simulation_status !== 'idle' && state.simulation_status !== 'completed') {
            statusRef.current = state.simulation_status
            const savedRouteIndex = state.current_route_index || 0
            setCurrentRouteIndex(savedRouteIndex)
            
            // Setup route first, then resume simulation
            if (restoredLocation) {
              // Wait for route to be set up
              const setupAndResume = async () => {
                await setupRoute()
                
                // Wait a bit for routePoints to be populated
                const checkRoute = setInterval(() => {
                  if (routePoints.length > 0) {
                    clearInterval(checkRoute)
                    // Resume from saved position
                    const resumeIndex = Math.min(savedRouteIndex, routePoints.length - 1)
                    setCurrentRouteIndex(resumeIndex)
                    
                    // Update current location to saved position
                    if (routePoints[resumeIndex]) {
                      const savedPoint = routePoints[resumeIndex]
                      setCurrentLocation(savedPoint)
                      setMapCenter([savedPoint.lat, savedPoint.lng])
                    }
                    
                    // Resume simulation if not completed
                    if (state.simulation_status !== 'completed' && !isSimulating) {
                      // Start from saved index
                      startSimulationFromIndex(restoredDelivery, resumeIndex, state.simulation_status)
                    }
                  }
                }, 500)
                
                // Timeout after 10 seconds
                setTimeout(() => clearInterval(checkRoute), 10000)
              }
              
              setupAndResume()
            }
          }
        }
      }
    } catch (err) {
      console.error('Failed to restore delivery state:', err)
    }
  }
  
  const startSimulationFromIndex = (delivery, startIndex, simStatus) => {
    if (!delivery || routePoints.length === 0 || isSimulating) return

    setIsSimulating(true)
    statusRef.current = simStatus || 'going_to_pickup'
    setCurrentRouteIndex(startIndex)

    const pickupIndex = Math.floor(routePoints.length / 2)
    let currentIndex = startIndex
    let pickupReached = simStatus === 'at_pickup' || simStatus === 'going_to_delivery' || currentIndex >= pickupIndex

    simulationRef.current = setInterval(() => {
      if (statusRef.current === 'at_pickup') return

      currentIndex += 1

      if (statusRef.current === 'going_to_pickup' && currentIndex >= pickupIndex && !pickupReached) {
        statusRef.current = 'at_pickup'
        pickupReached = true
        setCurrentRouteIndex(pickupIndex)
        
        const pickupPoint = routePoints[pickupIndex]
        sendLocationViaWebSocket(pickupPoint, delivery.delivery_id, pickupIndex, 'at_pickup')
        setCurrentLocation(pickupPoint)
        setMapCenter([pickupPoint.lat, pickupPoint.lng])
        
        handleUpdateStatus('in_progress')
          .then(() => {
            setTimeout(() => {
              statusRef.current = 'going_to_delivery'
            }, 3000)
          })

        return
      }

      if (statusRef.current === 'going_to_delivery' && currentIndex >= routePoints.length) {
        statusRef.current = 'completed'
        setCurrentRouteIndex(routePoints.length - 1)
        const finalPoint = routePoints[routePoints.length - 1]
        sendLocationViaWebSocket(finalPoint, delivery.delivery_id, routePoints.length - 1, 'completed')
        setCurrentLocation(finalPoint)
        setMapCenter([finalPoint.lat, finalPoint.lng])
        handleUpdateStatus('completed')
        return
      }

      if (currentIndex < routePoints.length) {
        const point = routePoints[currentIndex]
        sendLocationViaWebSocket(point, delivery.delivery_id, currentIndex, statusRef.current)
        setCurrentLocation(point)
        setCurrentRouteIndex(currentIndex)
        setMapCenter([point.lat, point.lng])
      }
    }, 2000)
  }

  useEffect(() => {
    if (currentDelivery && currentLocation && currentDelivery.status === 'accepted') {
      setupRoute()
    }
  }, [currentDelivery, currentLocation])
  
  // Auto-start simulation when route is ready and delivery is accepted
  useEffect(() => {
    if (
      currentDelivery && 
      currentDelivery.status === 'accepted' && 
      routePoints.length > 0 && 
      currentLocation &&
      !isSimulating &&
      statusRef.current === 'accepted'
    ) {
      // Small delay to ensure everything is set up
      const timer = setTimeout(() => {
        if (statusRef.current === 'accepted' && !isSimulating) {
          statusRef.current = 'going_to_pickup'
          startSimulation(currentDelivery)
        }
      }, 1000)
      return () => clearTimeout(timer)
    }
  }, [routePoints.length, currentDelivery?.delivery_id, currentLocation?.lat, isSimulating])

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
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'delivery_assigned') {
          fetchActiveDeliveries()
        } else if (data.type === 'delivery_accepted') {
          fetchActiveDeliveries()
          if (data.data) {
            setCurrentDelivery({
              delivery_id: data.data.delivery_id,
              order_id: data.data.order_id,
              order_number: data.data.order_number,
              status: 'accepted',
              pickup_location: data.data.pickup_location,
              delivery_location: data.data.delivery_location
            })
          }
        } else if (data.type === 'location_update') {
          if (data.data.location) {
            setCurrentLocation(data.data.location)
          }
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
      const updatedDelivery = { ...delivery, status: 'accepted' }
      setCurrentDelivery(updatedDelivery)
      statusRef.current = 'accepted'
      fetchActiveDeliveries()
      
      // Ensure we have current location before setting up route
      if (!currentLocation) {
        await fetchCurrentLocation()
      }
      
      // Force route setup if not already done
      if (currentLocation && updatedDelivery.pickup_location && updatedDelivery.delivery_location) {
        await setupRoute()
      }
      
      // Wait a bit for route to be calculated, then start simulation
      // The useEffect will also handle this, but we do it here as a fallback
      setTimeout(() => {
        if (routePoints.length > 0 && currentLocation && statusRef.current === 'accepted' && !isSimulating) {
          statusRef.current = 'going_to_pickup'
          startSimulation(updatedDelivery)
        }
      }, 2000)
    } catch (err) {
      console.error('Failed to accept delivery:', err)
    }
  }

  const handleDenyDelivery = async (delivery) => {
    try {
      const result = await deliveryAPI.deny(delivery.delivery_id)
      fetchActiveDeliveries()
      if (result.order_cancelled) {
        alert('Order cancelled due to excessive denials (5 denials)')
      }
    } catch (err) {
      console.error('Failed to deny delivery:', err)
    }
  }

  const handleUpdateStatus = async (status) => {
    if (!currentDelivery || !currentLocation) return
    
    try {
      await deliveryAPI.updateStatus(
        currentDelivery.delivery_id,
        status,
        currentLocation,
        currentRouteIndex,
        statusRef.current
      )
      if (status === 'completed') {
        stopSimulation()
        setCurrentDelivery(null)
        fetchActiveDeliveries()
      }
    } catch (err) {
      console.error('Failed to update status:', err)
    }
  }

  const setupRoute = async () => {
    if (!currentDelivery || !currentLocation) return

    const pickup = currentDelivery.pickup_location
    const delivery = currentDelivery.delivery_location

    if (!pickup?.lat || !delivery?.lat) return

    try {
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

  const sendLocationViaWebSocket = async (location, deliveryId, routeIndex, simStatus) => {
    // Persist location to backend
    try {
      await deliveryAPI.updateStatus(
        deliveryId,
        null, // Don't change status, just update location
        location,
        routeIndex,
        simStatus
      )
    } catch (err) {
      console.error('Failed to persist location:', err)
    }
    
    // Send via WebSocket
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

  const startSimulation = (delivery, startIndex = 0) => {
    startSimulationFromIndex(delivery, startIndex, 'going_to_pickup')
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
    <div className="min-h-screen bg-background p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Rider Device</h1>
        <p className="text-muted-foreground mt-1">Manage your deliveries</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Rider Selection</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="relative z-50">
                <Select
                  value={activeRider?.id || ''}
                  onValueChange={(value) => {
                    const rider = riders.find(r => r.id === value)
                    setActiveRider(rider)
                  }}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select Rider" />
                  </SelectTrigger>
                  <SelectContent position="popper" className="z-[1000]">
                    {riders.map(rider => (
                      <SelectItem key={rider.id} value={rider.id}>
                        {rider.name} ({rider.phone})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className={`px-3 py-2 rounded-md text-sm flex items-center gap-2 ${wsConnected ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-400' : 'bg-red-400'}`} />
                {wsConnected ? 'Connected' : 'Disconnected'}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Delivery Requests</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {activeDeliveries.length === 0 ? (
                <p className="text-muted-foreground text-sm text-center py-4">
                  No active deliveries
                </p>
              ) : (
                activeDeliveries.map(delivery => (
                  <Card key={delivery.delivery_id} className="border">
                    <CardContent className="p-4">
                      <div className="space-y-3">
                        <div>
                          <p className="font-semibold flex items-center gap-2">
                            <Package className="w-4 h-4" />
                            {delivery.order_number}
                          </p>
                          <p className="text-xs text-muted-foreground mt-1">
                            Status: {delivery.status}
                          </p>
                          {delivery.pickup_location && (
                            <div className="text-xs text-muted-foreground mt-2">
                              <MapPin className="w-3 h-3 inline mr-1" />
                              {delivery.pickup_location.address}
                            </div>
                          )}
                        </div>
                        {delivery.status === 'assigned' && (
                          <div className="flex gap-2">
                            <Button
                              onClick={() => handleAcceptDelivery(delivery)}
                              className="flex-1"
                              size="sm"
                            >
                              <CheckCircle2 className="w-4 h-4 mr-1" />
                              Accept
                            </Button>
                            <Button
                              onClick={() => handleDenyDelivery(delivery)}
                              variant="destructive"
                              className="flex-1"
                              size="sm"
                            >
                              <XCircle className="w-4 h-4 mr-1" />
                              Deny
                            </Button>
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </CardContent>
          </Card>

          {currentDelivery && (
            <Card>
              <CardHeader>
                <CardTitle>Current Delivery</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <p className="font-semibold">{currentDelivery.order_number}</p>
                  <p className="text-sm text-muted-foreground">
                    Status: {statusRef.current}
                  </p>
                </div>
                {statusRef.current === 'at_pickup' && (
                  <Button
                    onClick={() => {
                      statusRef.current = 'going_to_delivery'
                      handleUpdateStatus('in_progress')
                    }}
                    className="w-full"
                  >
                    <Navigation className="w-4 h-4 mr-2" />
                    Start Delivery
                  </Button>
                )}
                {statusRef.current === 'going_to_delivery' && (
                  <Button
                    onClick={() => handleUpdateStatus('completed')}
                    className="w-full"
                    variant="default"
                  >
                    <CheckCircle2 className="w-4 h-4 mr-2" />
                    Mark Delivered
                  </Button>
                )}
              </CardContent>
            </Card>
          )}
        </div>

        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Delivery Map</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[600px] rounded-lg overflow-hidden border relative" style={{ zIndex: 1 }}>
                <MapContainer
                  center={mapCenter}
                  zoom={13}
                  style={{ height: '100%', width: '100%' }}
                  zoomControl={true}
                  key={`rider-map-${activeRider?.id || 'default'}`}
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
                      <Popup>
                        <strong>Pickup Location</strong><br />
                        {currentDelivery.pickup_location.address}
                      </Popup>
                    </Marker>
                  )}

                  {currentDelivery?.delivery_location?.lat && (
                    <Marker position={[currentDelivery.delivery_location.lat, currentDelivery.delivery_location.lng]}>
                      <Popup>
                        <strong>Delivery Location</strong><br />
                        {currentDelivery.delivery_location.address}
                      </Popup>
                    </Marker>
                  )}

                  {displayedRoute.length > 1 && (
                    <Polyline 
                      positions={displayedRoute.map(p => [p.lat, p.lng])} 
                      color="#3b82f6" 
                      weight={5}
                      opacity={0.9}
                    />
                  )}

                  {remainingRoute.length > 1 && (
                    <Polyline 
                      positions={remainingRoute.map(p => [p.lat, p.lng])} 
                      color="#6b7280" 
                      weight={3} 
                      dashArray="10, 5"
                      opacity={0.6}
                    />
                  )}
                </MapContainer>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

export default RiderDeviceImproved
