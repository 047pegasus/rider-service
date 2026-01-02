import React, { useState } from 'react'
import { orderAPI, deliveryAPI } from '../api/client'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { Button } from './ui/button'
import { AddressInput } from './AddressInput'
import { useApp } from '../context/AppContext'

function OrderPlacementNew({ onOrderPlaced }) {
  const { addOrder } = useApp()
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
        status: 'preparing',
      }

      const order = await orderAPI.create(orderData)
      addOrder(order.id, order)
      setSuccess(`Order ${order.order_number} created! Preparing order...`)
      
      // Order will auto-assign rider when ready (after 30-60 seconds)
      setTimeout(() => {
        onOrderPlaced(order.id)
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
    <Card>
      <CardHeader>
        <CardTitle>Place New Order</CardTitle>
        <CardDescription>Fill in the details and select locations on the map</CardDescription>
      </CardHeader>
      <CardContent>
        {error && (
          <div className="mb-4 p-3 rounded-md bg-destructive/10 text-destructive text-sm whitespace-pre-line">
            {error}
          </div>
        )}
        {success && (
          <div className="mb-4 p-3 rounded-md bg-green-500/10 text-green-400 text-sm">
            {success}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Customer Information</h3>
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
            <h3 className="text-lg font-semibold">Pickup Location</h3>
            <div className="space-y-2">
              <AddressInput
                label="Pickup Address"
                value={formData.pickup_address}
                onChange={handleInputChange}
                position={pickupLocation}
                onPositionChange={setPickupLocation}
                required
              />
            </div>
          </div>

          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Delivery Location</h3>
            <div className="space-y-2">
              <AddressInput
                label="Delivery Address"
                value={formData.delivery_address}
                onChange={handleInputChange}
                position={deliveryLocation}
                onPositionChange={setDeliveryLocation}
                required
              />
            </div>
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
  )
}

export default OrderPlacementNew
