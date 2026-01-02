import { useState, useCallback } from 'react'

export function useAddressAutocomplete() {
  const [suggestions, setSuggestions] = useState([])
  const [loading, setLoading] = useState(false)

  const searchAddress = useCallback(async (query) => {
    if (!query || query.length < 3) {
      setSuggestions([])
      return
    }

    setLoading(true)
    try {
      // Using Nominatim (OpenStreetMap geocoding)
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=5&addressdetails=1`,
        {
          headers: {
            'User-Agent': 'RiderService/1.0'
          }
        }
      )
      const data = await response.json()
      setSuggestions(data.map(item => ({
        display: item.display_name,
        address: item.display_name,
        lat: parseFloat(item.lat),
        lng: parseFloat(item.lon),
      })))
    } catch (error) {
      console.error('Address search error:', error)
      setSuggestions([])
    } finally {
      setLoading(false)
    }
  }, [])

  return { suggestions, loading, searchAddress }
}
