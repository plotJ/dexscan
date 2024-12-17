import { NextResponse } from 'next/server'
import { DexAnalyzer } from '@/lib/dexanalyzer'

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const pair = searchParams.get('pair')

  if (!pair) {
    return NextResponse.json(
      { error: 'Pair address is required' },
      { status: 400 }
    )
  }

  try {
    const analyzer = new DexAnalyzer()
    const pairData = await analyzer.get_pair_data(pair)
    
    if (!pairData || !pairData.pairs.length) {
      return NextResponse.json(
        { error: 'Pair not found' },
        { status: 404 }
      )
    }

    const analysis = await analyzer.analyze_price_movement(pairData)
    return NextResponse.json(analysis)
  } catch (error) {
    console.error('Error analyzing pair:', error)
    return NextResponse.json(
      { error: 'Failed to analyze pair' },
      { status: 500 }
    )
  }
}
