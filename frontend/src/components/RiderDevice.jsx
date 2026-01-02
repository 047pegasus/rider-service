import React, { useState, useEffect, useRef } from 'react'
import { MapContainer, TileLayer, Marker, Polyline, Popup } from 'react-leaflet'
import { riderAPI, orderAPI } from '../api/client'
import ReconnectingWebSocket from 'reconnecting-websocket'
import './RiderDevice.css'

// Helper function to calculate intermediate points between two coordinates
function calculateRoutePoints(start, end, numPoints = 50) {
  const points = []
  for (let i = 0; i <= numPoints; i++) {
    const ratio = i / numPoints
    const lat = start.lat + (end.lat - start.lat) * ratio
    const lng = start.lng + (end.lng - start.lng) * ratio
    points.push({ lat, lng })
  }
  return points
}

// Helper function to calculate distance between two points
function calculateDistance(lat1, lng1, lat2, lng2) {
  const R = 6371 // Earth's radius in km
  const dLat = (lat2 - lat1) * Math.PI / 180
  const dLng = (lng2 - lng1) * Math.PI / 180
  const a = 
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLng / 2) * Math.sin(dLng / 2)
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  return R * c
}

function RiderDevice() {
  const [riders, setRiders] = useState([])
  const [selectedRider, setSelectedRider] = useState(null)
  const [activeDeliveries, setActiveDeliveries] = useState([])
  const [selectedDelivery, setSelectedDelivery] = useState(null)
  const [currentLocation, setCurrentLocation] = useState(null)
  const [isSimulating, setIsSimulating] = useState(false)
  const [simulationStatus, setSimulationStatus] = useState('idle') // idle, going_to_pickup, at_pickup, going_to_delivery, at_delivery
  const [routePoints, setRoutePoints] = useState([])
  const [currentRouteIndex, setCurrentRouteIndex] = useState(0)
  const [speed, setSpeed] = useState(50) // km/h
  const [updateInterval, setUpdateInterval] = useState(2000) // ms
  const [wsConnected, setWsConnected] = useState(false)
  
  const simulationIntervalRef = useRef(null)
  const wsRef = useRef(null)

  useEffect(() => {
    fetchRiders()
  }, [])

  useEffect(() => {
    if (selectedRider) {
      fetchActiveDeliveries()
      fetchCurrentLocation()
      connectWebSocket()
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [selectedRider])

  useEffect(() => {
    if (selectedDelivery && currentLocation) {
      setupRoute()
    }
  }, [selectedDelivery, currentLocation])

  const fetchRiders = async () => {
    try {
      const data = await riderAPI.list()
      setRiders(data)
    } catch (err) {
      console.error('Failed to fetch riders:', err)
    }
  }

  const fetchActiveDeliveries = async () => {
    if (!selectedRider) return
    try {
      const data = await riderAPI.getActiveDeliveries(selectedRider.id)
      setActiveDeliveries(data)
      if (data.length > 0 && !selectedDelivery) {
        setSelectedDelivery(data[0])
      }
    } catch (err) {
      console.error('Failed to fetch active deliveries:', err)
    }
  }

  const fetchCurrentLocation = async () => {
    if (!selectedRider) return
    try {
      const location = await riderAPI.getLocation(selectedRider.id)
      if (location) {
        setCurrentLocation({ lat: location.lat, lng: location.lng })
      } else {
        // If no location, use a default location
        setCurrentLocation({ lat: 28.6139, lng: 77.2090 })
      }
    } catch (err) {
      console.error('Failed to fetch current location:', err)
      // Default to Delhi if location fetch fails
      setCurrentLocation({ lat: 28.6139, lng: 77.2090 })
    }
  }

  const connectWebSocket = () => {
    if (!selectedRider) return

    const wsUrl = `ws://localhost:8000/ws/riders/${selectedRider.id}/`
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

  const setupRoute = () => {
    if (!selectedDelivery || !currentLocation) return

    const pickup = selectedDelivery.pickup_location
    const delivery = selectedDelivery.delivery_location

    if (!pickup.lat || !delivery.lat) return

    // Calculate route: current location -> pickup -> delivery
    const route1 = calculateRoutePoints(currentLocation, pickup, 30)
    const route2 = calculateRoutePoints(pickup, delivery, 30)
    const fullRoute = [...route1, ...route2]

    setRoutePoints(fullRoute)
    setCurrentRouteIndex(0)
    setSimulationStatus('going_to_pickup')
  }

  const updateLocation = async (location, deliveryId = null) => {
    if (!selectedRider) return

    try {
      const locationData = {
        lat: location.lat,
        lng: location.lng,
        accuracy: 10.0,
        speed: speed,
        heading: 0,
        battery_level: 85,
      }

      if (deliveryId) {
        locationData.delivery_id = deliveryId
      }

      await riderAPI.updateLocation(selectedRider.id, locationData)
      setCurrentLocation(location)
    } catch (err) {
      console.error('Failed to update location:', err)
    }
  }

  const startSimulation = () => {
    if (!selectedDelivery || routePoints.length === 0) {
      alert('Please select a delivery and ensure route is set up')
      return
    }

    setIsSimulating(true)
    setCurrentRouteIndex(0)
    setSimulationStatus('going_to_pickup')

    const pickupPointIndex = Math.floor(routePoints.length / 2)
    const statusRef = { current: 'going_to_pickup' }
    let currentIndex = 0
    let pickupReached = false

    simulationIntervalRef.current = setInterval(() => {
      currentIndex += 1

      // Check if reached pickup
      if (statusRef.current === 'going_to_pickup' && currentIndex >= pickupPointIndex && !pickupReached) {
        statusRef.current = 'at_pickup'
        setSimulationStatus('at_pickup')
        setCurrentRouteIndex(pickupPointIndex)
        pickupReached = true
        
        // Update delivery status to in_progress
        updateDeliveryStatus('in_progress')
        
        // Wait at pickup, then continue to delivery
        setTimeout(() => {
          statusRef.current = 'going_to_delivery'
          setSimulationStatus('going_to_delivery')
        }, 3000)
        return
      }

      // Check if reached delivery
      if (statusRef.current === 'going_to_delivery' && currentIndex >= routePoints.length) {
        statusRef.current = 'at_delivery'
        setSimulationStatus('at_delivery')
        setCurrentRouteIndex(routePoints.length - 1)
        
        // Update delivery status to completed
        updateDeliveryStatus('completed')
        
        stopSimulation()
        return
      }

      if (currentIndex < routePoints.length) {
        const currentPoint = routePoints[currentIndex]
        updateLocation(currentPoint, selectedDelivery.delivery_id)
        setCurrentRouteIndex(currentIndex)
      }
    }, updateInterval)
  }

  const updateDeliveryStatus = async (status) => {
    if (!selectedDelivery) return
    
    try {
      const { deliveryAPI } = await import('../api/client')
      await deliveryAPI.updateStatus(
        selectedDelivery.delivery_id,
        status,
        currentLocation
      )
      // Refresh active deliveries to get updated status
      setTimeout(() => {
        fetchActiveDeliveries()
      }, 500)
    } catch (err) {
      console.error('Failed to update delivery status:', err)
    }
  }

  const stopSimulation = () => {
    if (simulationIntervalRef.current) {
      clearInterval(simulationIntervalRef.current)
      simulationIntervalRef.current = null
    }
    setIsSimulating(false)
  }

  const resetSimulation = () => {
    stopSimulation()
    setCurrentRouteIndex(0)
    setSimulationStatus('going_to_pickup')
    if (currentLocation && selectedDelivery) {
      setupRoute()
    }
  }

  const center = currentLocation || [28.6139, 77.2090]
  const displayedRoute = routePoints.slice(0, currentRouteIndex + 1)

  return (
    <div className="rider-device">
      <div className="rider-controls">
        <div className="control-section">
          <h3>Select Rider</h3>
          <select
            value={selectedRider?.id || ''}
            onChange={(e) => {
              const rider = riders.find(r => r.id === e.target.value)
              setSelectedRider(rider)
              setSelectedDelivery(null)
              setActiveDeliveries([])
            }}
            className="rider-select"
          >
            <option value="">-- Select Rider --</option>
            {riders.map(rider => (
              <option key={rider.id} value={rider.id}>
                {rider.name} ({rider.phone}) - {rider.vehicle_type}
              </option>
            ))}
          </select>
          <div className={`ws-status ${wsConnected ? 'connected' : 'disconnected'}`}>
            {wsConnected ? '🟢 Connected' : '🔴 Disconnected'}
          </div>
        </div>

        {selectedRider && (
          <>
            <div className="control-section">
              <h3>Active Deliveries</h3>
              {activeDeliveries.length === 0 ? (
                <p className="no-deliveries">No active deliveries</p>
              ) : (
                <select
                  value={selectedDelivery?.delivery_id || ''}
                  onChange={(e) => {
                    const delivery = activeDeliveries.find(d => d.delivery_id === e.target.value)
                    setSelectedDelivery(delivery)
                    resetSimulation()
                  }}
                  className="delivery-select"
                >
                  {activeDeliveries.map(delivery => (
                    <option key={delivery.delivery_id} value={delivery.delivery_id}>
                      {delivery.order_number} - {delivery.status}
                    </option>
                  ))}
                </select>
              )}
            </div>

            {selectedDelivery && (
              <div className="control-section">
                <h3>Simulation Controls</h3>
                <div className="simulation-info">
                  <p><strong>Status:</strong> {simulationStatus.replace('_', ' ')}</p>
                  <p><strong>Current Location:</strong> {
                    currentLocation 
                      ? `${currentLocation.lat.toFixed(6)}, ${currentLocation.lng.toFixed(6)}`
                      : 'Not set'
                  }</p>
                </div>
                <div className="simulation-controls">
                  <label>
                    Speed (km/h):
                    <input
                      type="number"
                      value={speed}
                      onChange={(e) => setSpeed(parseFloat(e.target.value) || 50)}
                      min="10"
                      max="100"
                      disabled={isSimulating}
                    />
                  </label>
                  <label>
                    Update Interval (ms):
                    <input
                      type="number"
                      value={updateInterval}
                      onChange={(e) => setUpdateInterval(parseInt(e.target.value) || 2000)}
                      min="500"
                      max="10000"
                      step="500"
                      disabled={isSimulating}
                    />
                  </label>
                </div>
                <div className="button-group">
                  {!isSimulating ? (
                    <button onClick={startSimulation} className="btn btn-start">
                      Start Simulation
                    </button>
                  ) : (
                    <button onClick={stopSimulation} className="btn btn-stop">
                      Stop Simulation
                    </button>
                  )}
                  <button onClick={resetSimulation} className="btn btn-reset" disabled={isSimulating}>
                    Reset
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      <div className="rider-map-section">
        <h3>Rider Location Map</h3>
        <MapContainer
          center={center}
          zoom={13}
          style={{ height: '600px', width: '100%' }}
          key={JSON.stringify(center)}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {currentLocation && (
            <Marker position={[currentLocation.lat, currentLocation.lng]}>
              <Popup>
                <strong>Current Location</strong><br />
                {selectedRider?.name || 'Rider'}<br />
                Speed: {speed} km/h
              </Popup>
            </Marker>
          )}

          {selectedDelivery && selectedDelivery.pickup_location.lat && (
            <Marker position={[selectedDelivery.pickup_location.lat, selectedDelivery.pickup_location.lng]}>
              <Popup>
                <strong>Pickup Location</strong><br />
                {selectedDelivery.pickup_location.address}
              </Popup>
            </Marker>
          )}

          {selectedDelivery && selectedDelivery.delivery_location.lat && (
            <Marker position={[selectedDelivery.delivery_location.lat, selectedDelivery.delivery_location.lng]}>
              <Popup>
                <strong>Delivery Location</strong><br />
                {selectedDelivery.delivery_location.address}
              </Popup>
            </Marker>
          )}

          {displayedRoute.length > 1 && (
            <Polyline 
              positions={displayedRoute.map(p => [p.lat, p.lng])} 
              color="blue" 
              weight={4}
            />
          )}

          {routePoints.length > displayedRoute.length && (
            <Polyline 
              positions={routePoints.slice(displayedRoute.length).map(p => [p.lat, p.lng])} 
              color="gray" 
              weight={2}
              dashArray="5, 5"
            />
          )}
        </MapContainer>
      </div>
    </div>
  )
}

export default RiderDevice
