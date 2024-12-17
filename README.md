# DexScan with BonkBot Integration

A comprehensive DEX scanner and trading bot that integrates with BonkBot and provides Telegram notifications, featuring a modern web interface for easy monitoring and control.

## Features

- Token analysis and verification using:
  - DexScreener API
  - RugCheck.xyz verification
  - Pocket Universe volume analysis
- Automated trading via BonkBot
- Real-time Telegram notifications
- Supply bundling detection
- Fake volume detection
- Stop loss and take profit management
- Modern web interface for:
  - Real-time token analysis
  - Trading controls
  - Configuration management
  - Security monitoring

## Backend Setup

1. Install Python requirements:
```bash
pip install -r requirements.txt
```

2. Configure the settings in `config.json`:

   - Add your API keys:
     ```json
     {
       "volume_verification": {
         "pocket_universe_api_key": "your-pocket-universe-api-key"
       },
       "telegram": {
         "bot_token": "your-telegram-bot-token",
         "chat_id": "your-chat-id",
         "bonkbot": {
           "api_key": "your-bonkbot-api-key",
           "chat_id": "your-bonkbot-chat-id"
         }
       }
     }
     ```

3. Customize trading parameters in `config.json`:
   - Adjust minimum liquidity and volume thresholds
   - Set stop loss and take profit percentages
   - Configure trade amount and slippage
   - Set blacklist tokens and deployers

## Web Interface Setup

1. Navigate to the web directory:
```bash
cd web
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

4. For production deployment:
```bash
npm run build
npm start
```

The web interface can also be deployed to Vercel for easy access:
1. Push your code to a Git repository
2. Connect your repository to Vercel
3. Configure environment variables in Vercel settings

## Usage

### Backend Service
Run the scanner:
```bash
python main.py
```

The script will:
1. Scan for tokens meeting your criteria
2. Verify tokens using RugCheck.xyz
3. Check for fake volume and supply bundling
4. Execute trades through BonkBot when conditions are met
5. Send notifications via Telegram

### Web Interface
Access the web dashboard at `http://localhost:3000` (or your Vercel deployment URL) to:
1. Monitor token analysis in real-time
2. Control trading operations
3. Configure trading parameters
4. View security checks and alerts

## Trading Features

- Automated trading via BonkBot with web controls
- Stop loss and take profit management
- Risk management through:
  - Liquidity checks
  - Volume verification
  - Contract verification
  - Supply analysis
- Web-based trading parameter configuration

## Notifications

Receive real-time notifications through:
- Telegram messages for:
  - Trade executions (buy/sell)
  - Stop loss/take profit triggers
  - Risk alerts
  - New pair discoveries
  - Price movements
- Web interface alerts for:
  - Security warnings
  - Trading status
  - Parameter updates

## Safety Features

- RugCheck.xyz integration with visual indicators
- Supply bundling detection
- Fake volume detection with detailed analysis
- Blacklist system for suspicious tokens and deployers
- Automatic deployer blacklisting for bundled supply tokens
- Real-time security monitoring through web interface

## Architecture

The system consists of two main components:

1. **Python Backend**
   - Handles token scanning and analysis
   - Manages trading operations
   - Integrates with external APIs
   - Processes real-time data

2. **Next.js Web Interface**
   - Provides user-friendly dashboard
   - Displays real-time analysis
   - Offers trading controls
   - Shows security status
   - Configures trading parameters

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
