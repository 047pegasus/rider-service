import React from 'react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from './components/ui/tabs'
import { useApp } from './context/AppContext'
import ClientPage from './components/ClientPage'
import RiderDeviceImproved from './components/RiderDeviceImproved'
import './App.css'

function App() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border sticky top-0 z-50 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold mb-4">🚴 Rider Service - Delivery Tracking</h1>
          <Tabs defaultValue="client" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="client">Client Portal</TabsTrigger>
              <TabsTrigger value="rider">Rider Device</TabsTrigger>
            </TabsList>
            <TabsContent value="client" className="mt-4">
              <ClientPage />
            </TabsContent>
            <TabsContent value="rider" className="mt-4">
              <RiderDeviceImproved />
            </TabsContent>
          </Tabs>
        </div>
      </header>
    </div>
  )
}

export default App
