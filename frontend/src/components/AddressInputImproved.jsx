import React, { useState, useRef, useEffect } from 'react'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { Card } from './ui/card'
import { useAddressAutocomplete } from '../hooks/useAddressAutocomplete'
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet'
import { Search } from 'lucide-react'

export function AddressInput({ label, value, onChange, position, onPositionChange, required }) {
  const [inputValue, setInputValue] = useState(value || '')
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [mapPosition, setMapPosition] = useState(position || [28.6139, 77.2090])
  const { suggestions, loading, searchAddress } = useAddressAutocomplete()
  const inputRef = useRef(null)
  const suggestionsRef = useRef(null)

  useEffect(() => {
    if (value) {
      setInputValue(value)
    }
  }, [value])

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(event.target) &&
        inputRef.current &&
        !inputRef.current.contains(event.target)
      ) {
        setShowSuggestions(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleInputChange = (e) => {
    const newValue = e.target.value
    setInputValue(newValue)
    onChange({ target: { name: e.target.name, value: newValue } })
    if (newValue.length >= 3) {
      searchAddress(newValue)
      setShowSuggestions(true)
    } else {
      setShowSuggestions(false)
    }
  }

  const handleSuggestionClick = (suggestion) => {
    setInputValue(suggestion.address)
    onChange({ target: { name: inputRef.current.name, value: suggestion.address } })
    if (onPositionChange) {
      onPositionChange({ lat: suggestion.lat, lng: suggestion.lng })
      setMapPosition([suggestion.lat, suggestion.lng])
    }
    setShowSuggestions(false)
  }

  const MapClickHandler = () => {
    useMapEvents({
      click(e) {
        const { lat, lng } = e.latlng
        setMapPosition([lat, lng])
        if (onPositionChange) {
          onPositionChange({ lat, lng })
        }
        // Reverse geocode to get address
        fetch(
          `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`,
          {
            headers: { 'User-Agent': 'RiderService/1.0' }
          }
        )
          .then(res => res.json())
          .then(data => {
            if (data.display_name) {
              setInputValue(data.display_name)
              onChange({ target: { name: inputRef.current.name, value: data.display_name } })
            }
          })
          .catch(console.error)
      },
    })
    return null
  }

  return (
    <div className="space-y-3">
      <Label htmlFor={label} className="text-sm font-medium">
        {label} {required && <span className="text-destructive">*</span>}
      </Label>
      <div className="relative">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            ref={inputRef}
            id={label}
            name={label.toLowerCase().replace(/\s+/g, '_')}
            value={inputValue}
            onChange={handleInputChange}
            onFocus={() => inputValue.length >= 3 && setShowSuggestions(true)}
            placeholder="Search address or click on map"
            required={required}
            className="pl-10"
          />
        </div>
        {showSuggestions && (suggestions.length > 0 || loading) && (
          <Card
            ref={suggestionsRef}
            className="absolute z-[1000] w-full mt-1 max-h-60 overflow-auto bg-card border shadow-lg"
          >
            {loading && (
              <div className="p-3 text-sm text-muted-foreground flex items-center gap-2">
                <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                Searching...
              </div>
            )}
            {!loading && suggestions.length === 0 && (
              <div className="p-3 text-sm text-muted-foreground">No addresses found</div>
            )}
            {suggestions.map((suggestion, idx) => (
              <div
                key={idx}
                className="p-3 hover:bg-accent cursor-pointer text-sm border-b last:border-b-0 transition-colors"
                onClick={() => handleSuggestionClick(suggestion)}
              >
                <p className="font-medium">{suggestion.display}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {suggestion.lat.toFixed(6)}, {suggestion.lng.toFixed(6)}
                </p>
              </div>
            ))}
          </Card>
        )}
      </div>
      <div className="h-64 rounded-lg overflow-hidden border bg-muted/50 relative" style={{ zIndex: 1 }}>
        <MapContainer
          center={mapPosition}
          zoom={13}
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <MapClickHandler />
          {position && <Marker position={[position.lat, position.lng]} />}
        </MapContainer>
      </div>
      {position && (
        <div className="text-xs text-muted-foreground flex items-center gap-2">
          <MapPin className="w-3 h-3" />
          Selected: {position.lat.toFixed(6)}, {position.lng.toFixed(6)}
        </div>
      )}
    </div>
  )
}
