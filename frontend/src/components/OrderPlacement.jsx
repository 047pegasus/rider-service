import React, { useState } from 'react'
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet'
import { orderAPI, deliveryAPI } from '../api/client'
import './OrderPlacement.css'

function LocationPicker({ position, onPositionChange, label }) {
  const [mapPosition, setMapPosition] = useState(position || [28.6139, 77.2090]) // Default to Delhi

  const MapClickHandler = () => {
    useMapEvents({
      click(e) {
        const { lat, lng } = e.latlng
        setMapPosition([lat, lng])
        onPositionChange({ lat, lng })
      },
    })
    return null
  }

  return (
    <div className="location-picker">
      <label>{label}</label>
      <div className="map-container">
        <MapContainer
          center={mapPosition}
          zoom={13}
          style={{ height: '300px', width: '100%' }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <MapClickHandler />
          {mapPosition && <Marker position={mapPosition} />}
        </MapContainer>
      </div>
      {position && (
        <div className="coordinates">
          Lat: {position.lat.toFixed(6)}, Lng: {position.lng.toFixed(6)}
        </div>
      )}
    </div>
  )
}

function OrderPlacement({ onOrderPlaced }) {
  const [formData, setFormData] = useState({
    customer_name: '',
    customer_phone: '',
    pickup_address: '',
    delivery_address: '',
    special_instructions: '',
  })
  
  const [pickupLocation, setPickupLocation] = useState(null)
  const [deliveryLocation, setDeliveryLocation] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

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
      setError('Please select both pickup and delivery locations on the map')
      setLoading(false)
      return
    }

    try {
      // Generate a unique order number
      const orderNumber = `ORD-${Date.now()}`
      
      // Generate a valid UUID v4 for customer_id
      const generateUUID = () => {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
          const r = Math.random() * 16 | 0
          const v = c === 'x' ? r : (r & 0x3 | 0x8)
          return v.toString(16)
        })
      }
      
      // Round coordinates to 8 decimal places (max_digits=10, decimal_places=8)
      const roundCoordinate = (coord) => {
        return parseFloat(coord.toFixed(8))
      }
      
      const orderData = {
        order_number: orderNumber,
        customer_id: generateUUID(),
        customer_name: formData.customer_name,
        customer_phone: formData.customer_phone,
        pickup_address: formData.pickup_address,
        pickup_lat: roundCoordinate(pickupLocation.lat),
        pickup_lng: roundCoordinate(pickupLocation.lng),
        delivery_address: formData.delivery_address,
        delivery_lat: roundCoordinate(deliveryLocation.lat),
        delivery_lng: roundCoordinate(deliveryLocation.lng),
        special_instructions: formData.special_instructions || null,
        status: 'pending',
      }

      const order = await orderAPI.create(orderData)
      setSuccess(`Order ${order.order_number} created successfully!`)
      
      // Automatically assign a rider
      try {
        const delivery = await deliveryAPI.assign(order.id)
        setSuccess(
          `Order ${order.order_number} created and rider assigned! Tracking ID: ${order.id}`
        )
        setTimeout(() => {
          onOrderPlaced(order.id)
        }, 2000)
      } catch (assignError) {
        const assignErrorMsg = assignError.response?.data?.detail || assignError.message || 'Unknown error'
        setError(`Order created but rider assignment failed: ${assignErrorMsg}`)
      }
    } catch (err) {
      // Handle validation errors
      let errorMessage = 'Failed to create order'
      
      if (err.response?.data) {
        const errors = err.response.data
        
        // Handle Django REST Framework validation errors
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
        } else if (errors.error) {
          errorMessage = errors.error
        } else if (typeof errors === 'string') {
          errorMessage = errors
        }
      } else if (err.message) {
        // Try to parse JSON error message
        try {
          const parsed = JSON.parse(err.message)
          if (parsed && typeof parsed === 'object') {
            const errorMessages = Object.entries(parsed)
              .map(([field, messages]) => {
                const fieldName = field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
                const msg = Array.isArray(messages) ? messages.join(', ') : String(messages)
                return `${fieldName}: ${msg}`
              })
              .join('\n')
            errorMessage = errorMessages
          } else {
            errorMessage = err.message
          }
        } catch {
          errorMessage = err.message
        }
      }
      
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="order-placement">
      <h2>Place New Order</h2>
      
      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <form onSubmit={handleSubmit} className="order-form">
        <div className="form-section">
          <h3>Customer Information</h3>
          <div className="form-group">
            <label>Customer Name *</label>
            <input
              type="text"
              name="customer_name"
              value={formData.customer_name}
              onChange={handleInputChange}
              required
            />
          </div>
          <div className="form-group">
            <label>Phone Number *</label>
            <input
              type="tel"
              name="customer_phone"
              value={formData.customer_phone}
              onChange={handleInputChange}
              required
              pattern="[0-9]{10}"
              placeholder="10 digit phone number"
            />
          </div>
        </div>

        <div className="form-section">
          <h3>Pickup Location</h3>
          <div className="form-group">
            <label>Pickup Address *</label>
            <input
              type="text"
              name="pickup_address"
              value={formData.pickup_address}
              onChange={handleInputChange}
              required
              placeholder="Enter pickup address"
            />
          </div>
          <LocationPicker
            position={pickupLocation}
            onPositionChange={setPickupLocation}
            label="Click on map to set pickup location"
          />
        </div>

        <div className="form-section">
          <h3>Delivery Location</h3>
          <div className="form-group">
            <label>Delivery Address *</label>
            <input
              type="text"
              name="delivery_address"
              value={formData.delivery_address}
              onChange={handleInputChange}
              required
              placeholder="Enter delivery address"
            />
          </div>
          <LocationPicker
            position={deliveryLocation}
            onPositionChange={setDeliveryLocation}
            label="Click on map to set delivery location"
          />
        </div>

        <div className="form-section">
          <div className="form-group">
            <label>Special Instructions</label>
            <textarea
              name="special_instructions"
              value={formData.special_instructions}
              onChange={handleInputChange}
              rows="3"
              placeholder="Any special delivery instructions..."
            />
          </div>
        </div>

        <button type="submit" disabled={loading} className="submit-button">
          {loading ? 'Creating Order...' : 'Place Order & Assign Rider'}
        </button>
      </form>
    </div>
  )
}

export default OrderPlacement
