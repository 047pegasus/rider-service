import React, { useState, useEffect, useRef } from 'react'
import { MapContainer, TileLayer, Marker, Polyline, Popup } from 'react-leaflet'
import { useMap } from 'react-leaflet'
import L from 'leaflet'
import { orderAPI } from '../api/client'
import { routingAPI } from '../api/routing'
import ReconnectingWebSocket from 'reconnecting-websocket'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { Button } from './ui/button'
import { AddressInput } from './AddressInput'
import { useApp } from '../context/AppContext'
import { Search, Package, MapPin, CheckCircle2, Clock, Truck } from 'lucide-react'

// Create bike icon
const createBikeIcon = () => {
  return L.divIcon({
    className: 'bike-marker',
    html: '<div style="font-size: 30px;">🚴</div>',
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

function ClientPage() {
  const { orders, addOrder, updateOrder } = useApp()
  const [activeOrders, setActiveOrders] = useState([])
  const [selectedOrder, setSelectedOrder] = useState(null)
  const [showOrderForm, setShowOrderForm] = useState(false)
  const [formData, setFormData] = useState({
    customer_name: '',
    customer_phone: '',
    pickup_address: '',
    delivery_address: '',
    special_instructions: '',
  })
  const [pickupLocation, setPickupLocation] = useState(null)
  const [deliveryLocation, setDeliveryLocation] = useState(null)
  const [riderLocation, setRiderLocation] = useState(null)
  const [routePoints, setRoutePoints] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  const [wsConnected, setWsConnected] = useState(false)
  const wsRef = useRef(null)

  useEffect(() => {
    fetchActiveOrders()
    const interval = setInterval(fetchActiveOrders, 5000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (selectedOrder) {
      connectWebSocket()
      fetchOrderDetails()
    }
    return () => {
      if (wsRef.current) wsRef.current.close()
    }
  }, [selectedOrder])

  const fetchActiveOrders = async () => {
    try {
      const customerId = localStorage.getItem('customer_id') || generateUUID()
      localStorage.setItem('customer_id', customerId)
      
      const allOrders = await orderAPI.list()
      const myOrders = allOrders.filter(o => 
        o.customer_id === customerId && 
        !['delivered', 'cancelled'].includes(o.status)
      )
      setActiveOrders(myOrders)
      
      // Update context
      myOrders.forEach(order => {
        addOrder(order.id, order)
      })
    } catch (err) {
      console.error('Failed to fetch orders:', err)
    }
  }

  const fetchOrderDetails = async () => {
    if (!selectedOrder) return
    
    try {
      const trackingInfo = await orderAPI.track(selectedOrder.id || selectedOrder.order_number)
      updateOrder(selectedOrder.id, trackingInfo)
      
      if (trackingInfo.current_location) {
        setRiderLocation(trackingInfo.current_location)
      }
      
      if (trackingInfo.pickup_lat && trackingInfo.delivery_lat) {
        buildRoute(trackingInfo)
      }
    } catch (err) {
      console.error('Failed to fetch order details:', err)
    }
  }

  const buildRoute = async (orderData) => {
    if (!orderData.pickup_lat || !orderData.delivery_lat) return

    try {
      const route = await routingAPI.calculateRoute(
        { lat: orderData.pickup_lat, lng: orderData.pickup_lng },
        { lat: orderData.delivery_lat, lng: orderData.delivery_lng }
      )
      setRoutePoints(route)
    } catch (err) {
      console.error('Route calculation error:', err)
    }
  }

  const connectWebSocket = () => {
    if (!selectedOrder) return

    const wsOrderId = selectedOrder.id || selectedOrder.order_id
    if (!wsOrderId || wsOrderId.length < 30) return

    const wsUrl = `ws://localhost:8000/ws/orders/${wsOrderId}/`
    const ws = new ReconnectingWebSocket(wsUrl)
    
    ws.onopen = () => {
      setWsConnected(true)
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        if (data.type === 'rider_assigned') {
          updateOrder(selectedOrder.id, {
            ...selectedOrder,
            rider: data.data.rider,
            status: 'assigned'
          })
          fetchOrderDetails()
        } else if (data.type === 'location_update') {
          if (data.data.location) {
            setRiderLocation(data.data.location)
          }
        } else if (data.type === 'order_update') {
          const updated = {
            ...selectedOrder,
            status: data.data.order_status || data.data.status || selectedOrder.status
          }
          setSelectedOrder(updated)
          updateOrder(selectedOrder.id, updated)
          fetchOrderDetails()
        } else if (data.type === 'order_cancelled') {
          const updated = {
            ...selectedOrder,
            status: 'cancelled'
          }
          setSelectedOrder(updated)
          updateOrder(selectedOrder.id, updated)
          fetchActiveOrders()
        }
      } catch (err) {
        console.error('Error parsing WebSocket message:', err)
      }
    }

    ws.onerror = () => setWsConnected(false)
    ws.onclose = () => setWsConnected(false)

    wsRef.current = ws
  }

  const generateUUID = () => {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0
      const v = c === 'x' ? r : (r & 0x3 | 0x8)
      return v.toString(16)
    })
  }

  const roundCoordinate = (coord) => {
    return parseFloat(coord.toFixed(8))
  }

  const handleInputChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSuccess(null)

    if (!pickupLocation || !deliveryLocation) {
      setError('Please select both pickup and delivery locations')
      setLoading(false)
      return
    }

    try {
      const orderNumber = `ORD-${Date.now()}`
      const customerId = localStorage.getItem('customer_id') || generateUUID()
      localStorage.setItem('customer_id', customerId)
      
      const orderData = {
        order_number: orderNumber,
        customer_id: customerId,
        customer_name: formData.customer_name,
        customer_phone: formData.customer_phone,
        pickup_address: formData.pickup_address,
        pickup_lat: roundCoordinate(pickupLocation.lat),
        pickup_lng: roundCoordinate(pickupLocation.lng),
        delivery_address: formData.delivery_address,
        delivery_lat: roundCoordinate(deliveryLocation.lat),
        delivery_lng: roundCoordinate(deliveryLocation.lng),
        special_instructions: formData.special_instructions || null,
        status: 'preparing',
      }

      const order = await orderAPI.create(orderData)
      addOrder(order.id, order)
      setSuccess(`Order ${order.order_number} created! Preparing order...`)
      
      // Reset form
      setFormData({
        customer_name: '',
        customer_phone: '',
        pickup_address: '',
        delivery_address: '',
        special_instructions: '',
      })
      setPickupLocation(null)
      setDeliveryLocation(null)
      setShowOrderForm(false)
      
      // Refresh orders
      setTimeout(() => {
        fetchActiveOrders()
        setSelectedOrder(order)
      }, 2000)
    } catch (err) {
      let errorMessage = 'Failed to create order'
      if (err.response?.data) {
        const errors = err.response.data
        if (typeof errors === 'object' && !Array.isArray(errors)) {
          const errorMessages = Object.entries(errors)
            .map(([field, messages]) => {
              const fieldName = field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
              const msg = Array.isArray(messages) ? messages.join(', ') : String(messages)
              return `${fieldName}: ${msg}`
            })
            .join('\n')
          errorMessage = errorMessages
        } else if (errors.detail) {
          errorMessage = errors.detail
        }
      } else if (err.message) {
        errorMessage = err.message
      }
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const handleCompletePayment = async (orderId) => {
    try {
      await orderAPI.completePayment(orderId)
      setSuccess('Payment completed successfully!')
      fetchActiveOrders()
    } catch (err) {
      setError(err.message || 'Failed to complete payment')
    }
  }

  const getStatusColor = (status) => {
    const colors = {
      pending: 'bg-gray-500/20 text-gray-400',
      preparing: 'bg-yellow-500/20 text-yellow-400',
      ready: 'bg-blue-500/20 text-blue-400',
      assigned: 'bg-purple-500/20 text-purple-400',
      accepted: 'bg-purple-500/20 text-purple-400',
      picked_up: 'bg-orange-500/20 text-orange-400',
      in_transit: 'bg-indigo-500/20 text-indigo-400',
      delivered: 'bg-green-500/20 text-green-400',
      cancelled: 'bg-red-500/20 text-red-400',
    }
    return colors[status] || 'bg-gray-500/20 text-gray-400'
  }

  const getStatusIcon = (status) => {
    if (status === 'delivered') return <CheckCircle2 className="w-4 h-4" />
    if (status === 'in_transit' || status === 'picked_up') return <Truck className="w-4 h-4" />
    return <Clock className="w-4 h-4" />
  }

  const center = riderLocation
    ? [riderLocation.lat, riderLocation.lng]
    : selectedOrder?.pickup_lat
    ? [parseFloat(selectedOrder.pickup_lat), parseFloat(selectedOrder.pickup_lng)]
    : [28.6139, 77.2090]

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Delivery Service</h1>
            <p className="text-muted-foreground mt-1">Place and track your orders</p>
          </div>
          <Button onClick={() => setShowOrderForm(!showOrderForm)}>
            {showOrderForm ? 'Cancel' : '+ New Order'}
          </Button>
        </div>

        {error && (
          <Card className="border-destructive">
            <CardContent className="pt-6">
              <div className="text-destructive text-sm whitespace-pre-line">{error}</div>
            </CardContent>
          </Card>
        )}

        {success && (
          <Card className="border-green-500">
            <CardContent className="pt-6">
              <div className="text-green-400 text-sm">{success}</div>
            </CardContent>
          </Card>
        )}

        {showOrderForm && (
          <Card>
            <CardHeader>
              <CardTitle>Place New Order</CardTitle>
              <CardDescription>Fill in the details and select locations</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="customer_name">Customer Name *</Label>
                    <Input
                      id="customer_name"
                      name="customer_name"
                      value={formData.customer_name}
                      onChange={handleInputChange}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="customer_phone">Phone Number *</Label>
                    <Input
                      id="customer_phone"
                      name="customer_phone"
                      type="tel"
                      value={formData.customer_phone}
                      onChange={handleInputChange}
                      required
                      pattern="[0-9]{10}"
                      placeholder="10 digit phone number"
                    />
                  </div>
                </div>

                <div className="space-y-4">
                  <AddressInput
                    label="Pickup Address"
                    value={formData.pickup_address}
                    onChange={handleInputChange}
                    position={pickupLocation}
                    onPositionChange={setPickupLocation}
                    required
                  />
                </div>

                <div className="space-y-4">
                  <AddressInput
                    label="Delivery Address"
                    value={formData.delivery_address}
                    onChange={handleInputChange}
                    position={deliveryLocation}
                    onPositionChange={setDeliveryLocation}
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="special_instructions">Special Instructions</Label>
                  <textarea
                    id="special_instructions"
                    name="special_instructions"
                    value={formData.special_instructions}
                    onChange={handleInputChange}
                    rows="3"
                    className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                    placeholder="Any special delivery instructions..."
                  />
                </div>

                <Button type="submit" disabled={loading} className="w-full">
                  {loading ? 'Creating Order...' : 'Place Order'}
                </Button>
              </form>
            </CardContent>
          </Card>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Package className="w-5 h-5" />
                  Active Orders
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {activeOrders.length === 0 ? (
                  <p className="text-muted-foreground text-sm text-center py-4">
                    No active orders. Place a new order to get started.
                  </p>
                ) : (
                  activeOrders.map(order => (
                    <Card
                      key={order.id}
                      className={`cursor-pointer transition-all hover:shadow-md ${
                        selectedOrder?.id === order.id ? 'border-primary border-2 shadow-md' : 'border'
                      }`}
                      onClick={() => {
                        setSelectedOrder(order)
                        fetchOrderDetails()
                      }}
                    >
                      <CardContent className="p-4">
                        <div className="space-y-2">
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <p className="font-semibold text-base">{order.order_number}</p>
                              <div className="flex items-center gap-2 mt-2">
                                <span className={`px-2 py-1 rounded-md text-xs font-medium flex items-center gap-1 ${getStatusColor(order.status)}`}>
                                  {getStatusIcon(order.status)}
                                  {order.status.replace('_', ' ').toUpperCase()}
                                </span>
                              </div>
                            </div>
                          </div>
                          {order.rider && (
                            <div className="pt-2 border-t">
                              <p className="text-xs text-muted-foreground">
                                <span className="font-medium">Rider:</span> {order.rider.name}
                              </p>
                              <p className="text-xs text-muted-foreground">
                                {order.rider.phone}
                              </p>
                            </div>
                          )}
                          <div className="text-xs text-muted-foreground">
                            <p className="truncate"><strong>From:</strong> {order.pickup_address}</p>
                            <p className="truncate"><strong>To:</strong> {order.delivery_address}</p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))
                )}
              </CardContent>
            </Card>
          </div>

          <div className="lg:col-span-2">
            {selectedOrder ? (
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle>{selectedOrder.order_number}</CardTitle>
                      <CardDescription className="flex items-center gap-2 mt-1">
                        <span className={`px-2 py-1 rounded text-xs ${getStatusColor(selectedOrder.status)}`}>
                          {selectedOrder.status.replace('_', ' ')}
                        </span>
                        {wsConnected && (
                          <span className="text-xs text-green-400">● Live</span>
                        )}
                      </CardDescription>
                    </div>
                    {selectedOrder.status === 'delivered' && !selectedOrder.payment_completed && (
                      <Button
                        onClick={() => handleCompletePayment(selectedOrder.id)}
                        variant="default"
                        className="bg-green-600 hover:bg-green-700"
                      >
                        <CheckCircle2 className="w-4 h-4 mr-2" />
                        Complete Payment
                      </Button>
                    )}
                    {selectedOrder.payment_completed && (
                      <span className="px-3 py-1 rounded-md bg-green-500/20 text-green-400 text-sm flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4" />
                        Payment Completed
                      </span>
                    )}
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {selectedOrder.rider && (
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <p className="text-sm text-muted-foreground">Rider</p>
                          <p className="font-medium">{selectedOrder.rider.name}</p>
                          <p className="text-sm text-muted-foreground">{selectedOrder.rider.phone}</p>
                        </div>
                        <div>
                          <p className="text-sm text-muted-foreground">Status</p>
                          <p className="font-medium">{selectedOrder.status}</p>
                        </div>
                      </div>
                    )}

                    <div className="h-[600px] rounded-lg overflow-hidden border shadow-sm">
                      <MapContainer
                        center={center}
                        zoom={13}
                        style={{ height: '100%', width: '100%' }}
                        zoomControl={true}
                        key={`map-${selectedOrder.id}`}
                        whenCreated={(mapInstance) => {
                          // Store map instance to prevent zoom reset
                          if (riderLocation) {
                            mapInstance.setView([riderLocation.lat, riderLocation.lng], 13, { animate: false })
                          }
                        }}
                      >
                        <TileLayer
                          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                        />
                        
                        {selectedOrder.pickup_lat && selectedOrder.pickup_lng && (
                          <Marker 
                            position={[parseFloat(selectedOrder.pickup_lat), parseFloat(selectedOrder.pickup_lng)]}
                            icon={L.divIcon({
                              className: 'pickup-marker',
                              html: '<div style="background: #10b981; width: 20px; height: 20px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>',
                              iconSize: [20, 20],
                              iconAnchor: [10, 10]
                            })}
                          >
                            <Popup>
                              <strong>📍 Pickup Location</strong><br />
                              {selectedOrder.pickup_address}
                            </Popup>
                          </Marker>
                        )}

                        {riderLocation?.lat && riderLocation?.lng && (
                          <AnimatedRiderMarker position={riderLocation}>
                            <Popup>
                              <strong>🚴 Rider Location</strong><br />
                              {selectedOrder.rider?.name || 'Rider'}<br />
                              {riderLocation.speed && `Speed: ${riderLocation.speed} km/h`}
                            </Popup>
                          </AnimatedRiderMarker>
                        )}

                        {selectedOrder.delivery_lat && selectedOrder.delivery_lng && (
                          <Marker 
                            position={[parseFloat(selectedOrder.delivery_lat), parseFloat(selectedOrder.delivery_lng)]}
                            icon={L.divIcon({
                              className: 'delivery-marker',
                              html: '<div style="background: #f59e0b; width: 20px; height: 20px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>',
                              iconSize: [20, 20],
                              iconAnchor: [10, 10]
                            })}
                          >
                            <Popup>
                              <strong>🎯 Delivery Location</strong><br />
                              {selectedOrder.delivery_address}
                            </Popup>
                          </Marker>
                        )}

                        {routePoints.length > 1 && (
                          <Polyline 
                            positions={routePoints.map(p => [p.lat, p.lng])} 
                            color="#3b82f6" 
                            weight={4}
                            opacity={0.8}
                          />
                        )}

                        {riderLocation && selectedOrder.pickup_lat && (
                          <>
                            <Polyline 
                              positions={[
                                [parseFloat(selectedOrder.pickup_lat), parseFloat(selectedOrder.pickup_lng)],
                                [riderLocation.lat, riderLocation.lng]
                              ]} 
                              color="#10b981" 
                              weight={3}
                              dashArray="10, 5"
                              opacity={0.7}
                            />
                            {riderLocation.lat > parseFloat(selectedOrder.pickup_lat) && selectedOrder.delivery_lat && (
                              <Polyline 
                                positions={[
                                  [riderLocation.lat, riderLocation.lng],
                                  [parseFloat(selectedOrder.delivery_lat), parseFloat(selectedOrder.delivery_lng)]
                                ]} 
                                color="#f59e0b" 
                                weight={3}
                                dashArray="10, 5"
                                opacity={0.7}
                              />
                            )}
                          </>
                        )}
                      </MapContainer>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardContent className="py-12 text-center">
                  <Package className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">Select an order to track its delivery</p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default ClientPage
