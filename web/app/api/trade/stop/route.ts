import { NextResponse } from 'next/server'
import { spawn } from 'child_process'
import path from 'path'

export async function POST(request: Request) {
  try {
    const { pairAddress } = await request.json()

    if (!pairAddress) {
      return NextResponse.json(
        { error: 'Pair address is required' },
        { status: 400 }
      )
    }

    const pythonPath = process.env.PYTHON_PATH || 'python'
    const scriptPath = path.join(process.cwd(), '..', 'main.py')

    const pythonProcess = spawn(pythonPath, [
      scriptPath,
      '--trade',
      pairAddress,
      '--action',
      'stop'
    ])

    pythonProcess.stderr.on('data', (data) => {
      console.error(`Python Error: ${data}`)
    })

    return NextResponse.json({ status: 'Trading stopped' })
  } catch (error) {
    console.error('Error stopping trading:', error)
    return NextResponse.json(
      { error: 'Failed to stop trading' },
      { status: 500 }
    )
  }
}
