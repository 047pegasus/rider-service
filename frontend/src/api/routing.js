/**
 * Route calculation API client
 * Uses backend routing service (OSRM) for accurate routes
 */
import apiClient from './client'

export const routingAPI = {
  calculateRoute: async (start, end, viaPoints = []) => {
    try {
      // For now, use frontend calculation with OSRM fallback
      // In production, this should call backend routing service
      const coords = [start, ...viaPoints, end]
        .map(p => `${p.lng},${p.lat}`)
        .join(';')
      
      const response = await fetch(
        `https://router.project-osrm.org/route/v1/driving/${coords}?overview=full&geometries=geojson`
      )
      
      if (response.ok) {
        const data = await response.json()
        if (data.code === 'Ok' && data.routes?.[0]) {
          const geometry = data.routes[0].geometry.coordinates
          return geometry.map(coord => ({ lat: coord[1], lng: coord[0] }))
        }
      }
      
      // Fallback to direct route
      return calculateDirectRoute(start, end)
    } catch (error) {
      console.error('Route calculation error:', error)
      return calculateDirectRoute(start, end)
    }
  }
}

function calculateDirectRoute(start, end, numPoints = 50) {
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
