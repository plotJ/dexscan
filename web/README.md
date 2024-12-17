# DexScan Web Interface

A modern web interface for the DexScan trading bot, built with Next.js and Shadcn/UI.

## Features

- Real-time token analysis dashboard
- Automated trading controls
- Security checks and volume analysis
- Configurable trading parameters
- Dark mode support
- Responsive design

## Setup

1. Install dependencies:
```bash
npm install
```

2. Create a `.env.local` file with the following variables:
```
PYTHON_PATH=python  # Path to your Python interpreter
```

3. Run the development server:
```bash
npm run dev
```

4. Build for production:
```bash
npm run build
```

## Deployment to Vercel

1. Push your code to a Git repository
2. Connect your repository to Vercel
3. Configure the following environment variables in Vercel:
   - `PYTHON_PATH`
   - Any API keys required by the Python backend

## Architecture

The web interface communicates with the Python backend through API routes. Each API route spawns a Python process to execute the corresponding command in the main.py script.

### Components
- Dashboard: Main interface with token analysis and trading controls
- Analysis Tab: Displays token metrics and security checks
- Trading Tab: Controls for automated trading
- Settings Tab: Configuration for trading parameters

### API Routes
- `/api/analyze`: Get token analysis
- `/api/trade/start`: Start automated trading
- `/api/trade/stop`: Stop automated trading

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
