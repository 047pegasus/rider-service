# Rider Service Frontend

Frontend application for the Rider Service delivery tracking system.

## Features

- **Order Placement**: Place new orders with interactive map for selecting pickup and delivery locations
- **Real-time Tracking**: Track orders in real-time using WebSocket connections
- **OpenStreetMap Integration**: Uses Leaflet and OpenStreetMap for map visualization
- **Rider Assignment**: Automatically assigns nearest available rider to orders
- **Live Location Updates**: Real-time updates of rider location during delivery

## Setup

1. Install dependencies:
```bash
npm install
```

2. Start development server:
```bash
npm run dev
```

The application will be available at `http://localhost:3000`

## Environment Variables

Create a `.env` file in the frontend directory:

```
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

## Build for Production

```bash
npm run build
```

The built files will be in the `dist` directory.
