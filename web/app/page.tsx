'use client'

import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useQuery } from '@tanstack/react-query'
import ErrorBoundary from '@/components/error-boundary'
import { Loading } from '@/components/ui/loading'

interface TokenAnalysis {
  token_name: string
  current_price: number
  price_change_24h: number
  volume_24h: number
  liquidity_usd: number
  event_type: string
  rugcheck_analysis?: {
    is_safe: boolean
    status: string
    warnings: string[]
  }
  volume_analysis?: {
    is_legitimate: boolean
    flags: string[]
    real_volume_ratio: number
  }
}

function DexScanDashboard() {
  const [pairAddress, setPairAddress] = useState('')
  const [isTrading, setIsTrading] = useState(false)

  const { data: analysis, isLoading } = useQuery<TokenAnalysis>({
    queryKey: ['tokenAnalysis', pairAddress],
    queryFn: async () => {
      if (!pairAddress) return null
      const res = await fetch(`/api/analyze?pair=${pairAddress}`)
      if (!res.ok) throw new Error('Failed to fetch analysis')
      return res.json()
    },
    enabled: Boolean(pairAddress),
  })

  const handleStartTrading = async () => {
    setIsTrading(true)
    try {
      const res = await fetch('/api/trade/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pairAddress }),
      })
      if (!res.ok) throw new Error('Failed to start trading')
    } catch (error) {
      console.error('Error starting trading:', error)
    }
  }

  const handleStopTrading = async () => {
    setIsTrading(false)
    try {
      const res = await fetch('/api/trade/stop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pairAddress }),
      })
      if (!res.ok) throw new Error('Failed to stop trading')
    } catch (error) {
      console.error('Error stopping trading:', error)
    }
  }

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-4xl font-bold mb-8">DexScan Dashboard</h1>
      
      <div className="mb-8">
        <Label htmlFor="pair-address">Pair Address</Label>
        <div className="flex gap-4">
          <Input
            id="pair-address"
            value={pairAddress}
            onChange={(e) => setPairAddress(e.target.value)}
            placeholder="Enter pair address..."
            className="flex-1"
          />
          <Button onClick={() => setPairAddress('')}>Clear</Button>
        </div>
      </div>

      <Tabs defaultValue="analysis" className="space-y-4">
        <TabsList>
          <TabsTrigger value="analysis">Analysis</TabsTrigger>
          <TabsTrigger value="trading">Trading</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>

        <TabsContent value="analysis">
          {isLoading ? (
            <Loading />
          ) : analysis ? (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              <Card>
                <CardHeader>
                  <CardTitle>Token Info</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div>Name: {analysis.token_name}</div>
                    <div>Price: ${analysis.current_price}</div>
                    <div>24h Change: {analysis.price_change_24h}%</div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Volume Analysis</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div>24h Volume: ${analysis.volume_24h}</div>
                    <div>Liquidity: ${analysis.liquidity_usd}</div>
                    {analysis.volume_analysis && (
                      <>
                        <div>Real Volume Ratio: {analysis.volume_analysis.real_volume_ratio}</div>
                        <div>Legitimate: {analysis.volume_analysis.is_legitimate ? 'Yes' : 'No'}</div>
                      </>
                    )}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Security Check</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {analysis.rugcheck_analysis && (
                      <>
                        <div>Status: {analysis.rugcheck_analysis.status}</div>
                        <div>Safe: {analysis.rugcheck_analysis.is_safe ? 'Yes' : 'No'}</div>
                        {analysis.rugcheck_analysis.warnings.length > 0 && (
                          <div>
                            <div>Warnings:</div>
                            <ul className="list-disc pl-4">
                              {analysis.rugcheck_analysis.warnings.map((warning, i) => (
                                <li key={i}>{warning}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          ) : null}
        </TabsContent>

        <TabsContent value="trading">
          <Card>
            <CardHeader>
              <CardTitle>Trading Controls</CardTitle>
              <CardDescription>Manage automated trading for this pair</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex gap-4">
                  <Button
                    onClick={handleStartTrading}
                    disabled={isTrading || !analysis?.rugcheck_analysis?.is_safe}
                  >
                    Start Trading
                  </Button>
                  <Button
                    onClick={handleStopTrading}
                    disabled={!isTrading}
                    variant="destructive"
                  >
                    Stop Trading
                  </Button>
                </div>
                {!analysis?.rugcheck_analysis?.is_safe && (
                  <div className="text-red-500">
                    Trading disabled: Token did not pass security checks
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="settings">
          <Card>
            <CardHeader>
              <CardTitle>Trading Settings</CardTitle>
              <CardDescription>Configure trading parameters</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="grid gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="stop-loss">Stop Loss (%)</Label>
                    <Input
                      id="stop-loss"
                      type="number"
                      placeholder="Enter stop loss percentage..."
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="take-profit">Take Profit (%)</Label>
                    <Input
                      id="take-profit"
                      type="number"
                      placeholder="Enter take profit percentage..."
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="trade-amount">Trade Amount (USD)</Label>
                    <Input
                      id="trade-amount"
                      type="number"
                      placeholder="Enter trade amount..."
                    />
                  </div>
                </div>
                <Button>Save Settings</Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default function Page() {
  return (
    <ErrorBoundary>
      <DexScanDashboard />
    </ErrorBoundary>
  )
}
