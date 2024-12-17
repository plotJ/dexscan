import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import logging
import json
import os
from collections import defaultdict
from typing import Dict, List, Optional
import asyncio
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
import threading
from queue import Queue

class TelegramNotifier:
    def __init__(self, config):
        self.config = config['telegram']
        self.bot = Bot(token=self.config['bot_token'])
        self.chat_id = self.config['chat_id']
        self.message_queue = Queue()
        self._start_message_worker()

    def _start_message_worker(self):
        def worker():
            async def send_messages():
                while True:
                    if not self.message_queue.empty():
                        msg = self.message_queue.get()
                        try:
                            await self.bot.send_message(
                                chat_id=self.chat_id,
                                text=msg,
                                parse_mode='HTML'
                            )
                        except Exception as e:
                            logging.error(f"Error sending Telegram message: {e}")
                    await asyncio.sleep(1)

            asyncio.run(send_messages())

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def send_notification(self, message: str):
        self.message_queue.put(message)

class BonkBotTrader:
    def __init__(self, config):
        self.config = config['telegram']['bonkbot']
        self.bot = Bot(token=self.config['api_key'])
        self.chat_id = self.config['chat_id']

    async def execute_trade(self, pair_address: str, action: str, amount_usd: float):
        """Execute trade through BonkBot"""
        try:
            command = f"/trade {action} {pair_address} {amount_usd}USD"
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=command
            )
            return True
        except Exception as e:
            logging.error(f"Error executing trade through BonkBot: {e}")
            return False

class DexAnalyzer:
    def __init__(self):
        self.base_url = "https://api.dexscreener.com/latest/dex/search"
        self.pocket_universe_url = "https://api.pocketuniverse.app/v1"
        self.rugcheck_url = "https://api.rugcheck.xyz/v1"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.setup_logging()
        self.load_config()
        self.setup_pocket_universe()
        self.setup_telegram()
        self.setup_bonkbot()
        self.active_trades = {}

    def setup_logging(self):
        logging.basicConfig(
            filename='dex_analysis.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def setup_pocket_universe(self):
        """Setup Pocket Universe API headers if API key is available."""
        if self.config['volume_verification'].get('pocket_universe_api_key'):
            self.pocket_headers = {
                'Authorization': f"Bearer {self.config['volume_verification']['pocket_universe_api_key']}",
                'Content-Type': 'application/json'
            }
        else:
            self.pocket_headers = None
            logging.warning("Pocket Universe API key not configured")

    def load_config(self):
        """Load configuration from config.json file."""
        try:
            with open('config.json', 'r') as f:
                self.config = json.load(f)
            logging.info("Configuration loaded successfully")
        except Exception as e:
            logging.error(f"Error loading configuration: {e}")
            self.config = {
                "filters": {},
                "blacklisted_tokens": [],
                "blacklisted_deployers": [],
                "suspicious_patterns": {},
                "monitoring": {},
                "volume_verification": {
                    "min_real_volume_ratio": 0.5,
                    "pocket_universe_api_key": "",
                    "min_unique_traders": 10,
                    "max_wash_trade_percentage": 50,
                    "suspicious_trade_patterns": {
                        "max_self_trades": 5,
                        "min_time_between_trades_seconds": 60,
                        "max_repetitive_amounts": 5
                    }
                }
            }

    def setup_telegram(self):
        """Setup Telegram notifications"""
        try:
            self.telegram = TelegramNotifier(self.config)
            logging.info("Telegram notifications initialized")
        except Exception as e:
            logging.error(f"Error setting up Telegram: {e}")
            self.telegram = None

    def setup_bonkbot(self):
        """Setup BonkBot trading"""
        try:
            self.bonkbot = BonkBotTrader(self.config)
            logging.info("BonkBot trading initialized")
        except Exception as e:
            logging.error(f"Error setting up BonkBot: {e}")
            self.bonkbot = None

    async def execute_trade(self, pair_data: Dict, action: str):
        """Execute trade through BonkBot and send notification"""
        if not self.bonkbot or not self.config['telegram']['bonkbot']['auto_trade']:
            return

        amount = self.config['telegram']['bonkbot']['trade_amount_usd']
        success = await self.bonkbot.execute_trade(
            pair_data['pairAddress'],
            action,
            amount
        )

        if success:
            self.notify_trade(pair_data, action, amount)
            if action == 'buy':
                self.active_trades[pair_data['pairAddress']] = {
                    'entry_price': float(pair_data['priceUsd']),
                    'amount': amount
                }
            elif action == 'sell':
                self.active_trades.pop(pair_data['pairAddress'], None)

    def notify_trade(self, pair_data: Dict, action: str, amount: float):
        """Send trade notification via Telegram"""
        if not self.telegram:
            return

        token_name = pair_data['baseToken']['name']
        price = float(pair_data['priceUsd'])
        message = (
            f"🤖 <b>Trade Executed</b>\n"
            f"Action: {'🟢 BUY' if action == 'buy' else '🔴 SELL'}\n"
            f"Token: {token_name}\n"
            f"Price: ${price:.8f}\n"
            f"Amount: ${amount:.2f}\n"
            f"Pair: {pair_data['pairAddress']}\n"
        )
        self.telegram.send_notification(message)

    def check_active_trades(self, pair_data: Dict):
        """Check active trades for stop loss and take profit"""
        if pair_data['pairAddress'] not in self.active_trades:
            return

        trade = self.active_trades[pair_data['pairAddress']]
        current_price = float(pair_data['priceUsd'])
        entry_price = trade['entry_price']
        price_change = ((current_price - entry_price) / entry_price) * 100

        config = self.config['telegram']['bonkbot']
        
        if price_change <= -config['stop_loss_percentage']:
            asyncio.create_task(self.execute_trade(pair_data, 'sell'))
            self.telegram.send_notification(
                f"🔴 Stop Loss triggered for {pair_data['baseToken']['name']}\n"
                f"Loss: {price_change:.2f}%"
            )
        elif price_change >= config['take_profit_percentage']:
            asyncio.create_task(self.execute_trade(pair_data, 'sell'))
            self.telegram.send_notification(
                f"🟢 Take Profit triggered for {pair_data['baseToken']['name']}\n"
                f"Profit: {price_change:.2f}%"
            )

    def is_token_blacklisted(self, token_address):
        """Check if token is blacklisted."""
        return token_address.lower() in (addr.lower() for addr in self.config['blacklisted_tokens'])

    def is_deployer_blacklisted(self, deployer_address):
        """Check if deployer is blacklisted."""
        return deployer_address.lower() in (addr.lower() for addr in self.config['blacklisted_deployers'])

    def check_volume_legitimacy(self, pair_data: Dict) -> Dict:
        """
        Check if the trading volume is legitimate using multiple methods.
        Returns a dictionary with analysis results.
        """
        volume_config = self.config['volume_verification']
        
        # Initialize result
        result = {
            'is_legitimate': True,
            'flags': [],
            'real_volume_ratio': 1.0,
            'unique_traders': 0
        }

        # Check with Pocket Universe if available
        if self.pocket_headers:
            pu_analysis = self.check_pocket_universe(pair_data['pairAddress'])
            if pu_analysis:
                result.update(pu_analysis)
                if not pu_analysis['is_legitimate']:
                    return result

        # Perform our own analysis
        trades = self.analyze_trading_patterns(pair_data)
        
        # Check unique traders
        if trades['unique_traders'] < volume_config['min_unique_traders']:
            result['flags'].append(f"Low unique traders: {trades['unique_traders']}")
            result['is_legitimate'] = False

        # Check wash trading patterns
        wash_trade_percentage = trades['wash_trade_count'] / max(trades['total_trades'], 1) * 100
        if wash_trade_percentage > volume_config['max_wash_trade_percentage']:
            result['flags'].append(f"High wash trading: {wash_trade_percentage:.2f}%")
            result['is_legitimate'] = False

        # Check trade timing patterns
        if trades['suspicious_timing_patterns']:
            result['flags'].append("Suspicious trade timing patterns detected")
            result['is_legitimate'] = False

        # Update result with additional metrics
        result.update({
            'wash_trade_percentage': wash_trade_percentage,
            'unique_traders': trades['unique_traders'],
            'suspicious_patterns': trades['suspicious_timing_patterns']
        })

        return result

    def check_pocket_universe(self, pair_address: str) -> Optional[Dict]:
        """Query Pocket Universe API for volume analysis."""
        if not self.pocket_headers:
            return None

        try:
            response = requests.get(
                f"{self.pocket_universe_url}/pairs/{pair_address}/analysis",
                headers=self.pocket_headers
            )
            response.raise_for_status()
            data = response.json()

            return {
                'is_legitimate': data['realVolumeRatio'] >= self.config['volume_verification']['min_real_volume_ratio'],
                'real_volume_ratio': data['realVolumeRatio'],
                'flags': data.get('flags', []),
                'source': 'pocket_universe'
            }
        except Exception as e:
            logging.error(f"Error querying Pocket Universe API: {e}")
            return None

    def analyze_trading_patterns(self, pair_data: Dict) -> Dict:
        """
        Analyze trading patterns to detect fake volume.
        """
        config = self.config['volume_verification']['suspicious_trade_patterns']
        
        # Get detailed trades (this would need to be implemented based on available data)
        trades = self.get_detailed_trades(pair_data)
        
        result = {
            'unique_traders': len(set(trade['trader'] for trade in trades)),
            'total_trades': len(trades),
            'wash_trade_count': 0,
            'suspicious_timing_patterns': []
        }

        # Analyze trade patterns
        trader_trades = defaultdict(list)
        amount_frequency = defaultdict(int)
        
        for trade in trades:
            trader = trade['trader']
            trader_trades[trader].append(trade)
            amount_frequency[trade['amount']] += 1

        # Check for self-trades and suspicious patterns
        for trader, trades_list in trader_trades.items():
            if len(trades_list) > config['max_self_trades']:
                result['wash_trade_count'] += len(trades_list)

            # Check time between trades
            trades_list.sort(key=lambda x: x['timestamp'])
            for i in range(1, len(trades_list)):
                time_diff = trades_list[i]['timestamp'] - trades_list[i-1]['timestamp']
                if time_diff < config['min_time_between_trades_seconds']:
                    result['suspicious_timing_patterns'].append(
                        f"Rapid trades from {trader}: {time_diff}s between trades"
                    )

        # Check for repetitive amounts
        for amount, count in amount_frequency.items():
            if count > config['max_repetitive_amounts']:
                result['suspicious_timing_patterns'].append(
                    f"Repetitive trade amount: {amount} used {count} times"
                )

        return result

    def get_detailed_trades(self, pair_data: Dict) -> List[Dict]:
        """
        Extract detailed trade information from pair data.
        This is a simplified version - in practice, you'd want to get this data
        from an on-chain source or detailed API.
        """
        trades = []
        
        # Convert basic transaction data to trade records
        for period in ['m5', 'h1', 'h6', 'h24']:
            if period in pair_data['txns']:
                timestamp_offset = {
                    'm5': 300,
                    'h1': 3600,
                    'h6': 21600,
                    'h24': 86400
                }[period]
                
                base_timestamp = int(time.time()) - timestamp_offset
                
                # Create synthetic trade records from transaction counts
                for _ in range(pair_data['txns'][period]['buys']):
                    trades.append({
                        'trader': f"trader_{len(trades)}",
                        'timestamp': base_timestamp + (len(trades) * 60),
                        'amount': pair_data['volume'][period] / max(pair_data['txns'][period]['buys'], 1),
                        'type': 'buy'
                    })
                
                for _ in range(pair_data['txns'][period]['sells']):
                    trades.append({
                        'trader': f"trader_{len(trades)}",
                        'timestamp': base_timestamp + (len(trades) * 60),
                        'amount': pair_data['volume'][period] / max(pair_data['txns'][period]['sells'], 1),
                        'type': 'sell'
                    })

        return trades

    def passes_filters(self, pair_data):
        """Check if pair passes all configured filters."""
        filters = self.config['filters']
        
        # Basic filters
        if float(pair_data['liquidity']['usd']) < filters.get('min_liquidity_usd', 0):
            logging.info(f"Pair {pair_data['pairAddress']} failed liquidity filter")
            return False
            
        if float(pair_data['volume']['h24']) < filters.get('min_volume_24h', 0):
            logging.info(f"Pair {pair_data['pairAddress']} failed volume filter")
            return False

        # Check RugCheck.xyz status
        rugcheck_result = self.check_rugcheck_status(
            pair_data['baseToken']['address'],
            pair_data['chainId']
        )
        
        if not rugcheck_result['is_safe']:
            logging.info(f"Pair {pair_data['pairAddress']} failed RugCheck verification: {rugcheck_result['status']}")
            pair_data['rugcheck_analysis'] = rugcheck_result
            return False

        # Check for supply bundling
        if rugcheck_result['is_supply_bundled']:
            logging.info(f"Pair {pair_data['pairAddress']} has bundled supply")
            # Add deployer to blacklist if supply is bundled
            if rugcheck_result.get('deployer'):
                self.config['blacklisted_deployers'].append(rugcheck_result['deployer'])
                self._save_blacklist_update(rugcheck_result['deployer'])
            return False

        # Store rugcheck analysis in pair data
        pair_data['rugcheck_analysis'] = rugcheck_result

        # Check volume legitimacy
        volume_check = self.check_volume_legitimacy(pair_data)
        if not volume_check['is_legitimate']:
            logging.info(f"Pair {pair_data['pairAddress']} failed volume legitimacy check: {volume_check['flags']}")
            pair_data['volume_analysis'] = volume_check
            return False

        # Age filter
        if 'pairCreatedAt' in pair_data:
            pair_age_hours = (datetime.now() - datetime.fromtimestamp(pair_data['pairCreatedAt']/1000)).total_seconds() / 3600
            if pair_age_hours < filters.get('min_age_hours', 0):
                logging.info(f"Pair {pair_data['pairAddress']} failed age filter")
                return False

        return True

    def check_rugcheck_status(self, token_address: str, chain_id: str) -> Dict:
        """
        Check token status on RugCheck.xyz
        """
        try:
            # First get the contract analysis
            response = requests.get(
                f"{self.rugcheck_url}/tokens/{chain_id}/{token_address}/analysis",
                headers=self.headers
            )
            response.raise_for_status()
            analysis = response.json()

            # Get supply information
            supply_response = requests.get(
                f"{self.rugcheck_url}/tokens/{chain_id}/{token_address}/supply",
                headers=self.headers
            )
            supply_response.raise_for_status()
            supply_data = supply_response.json()

            result = {
                'is_safe': analysis.get('status') == 'GOOD',
                'status': analysis.get('status', 'UNKNOWN'),
                'warnings': analysis.get('warnings', []),
                'is_supply_bundled': False,
                'deployer': analysis.get('deployer'),
                'supply_analysis': {}
            }

            # Check for supply bundling
            if supply_data:
                total_supply = float(supply_data.get('totalSupply', 0))
                circulating_supply = float(supply_data.get('circulatingSupply', 0))
                
                # Check for significant supply differences and unusual holder patterns
                result['is_supply_bundled'] = self._check_supply_bundling(supply_data)
                result['supply_analysis'] = {
                    'total_supply': total_supply,
                    'circulating_supply': circulating_supply,
                    'top_holders': supply_data.get('topHolders', []),
                    'holder_concentration': supply_data.get('holderConcentration', 0)
                }

            return result

        except Exception as e:
            logging.error(f"Error checking RugCheck.xyz: {e}")
            return {
                'is_safe': False,
                'status': 'ERROR',
                'warnings': [str(e)],
                'is_supply_bundled': False
            }

    def _check_supply_bundling(self, supply_data: Dict) -> bool:
        """
        Check if token supply shows signs of bundling
        """
        if not supply_data:
            return False

        suspicious_patterns = []

        # Check top holders concentration
        top_holders = supply_data.get('topHolders', [])
        if top_holders:
            # If top holder has more than 50% of supply
            if top_holders[0].get('percentage', 0) > 50:
                suspicious_patterns.append('Single holder dominance')

            # Check for multiple addresses with similar holdings
            similar_holdings = []
            for i in range(len(top_holders) - 1):
                for j in range(i + 1, len(top_holders)):
                    if abs(top_holders[i].get('percentage', 0) - top_holders[j].get('percentage', 0)) < 1:
                        similar_holdings.append((top_holders[i]['address'], top_holders[j]['address']))

            if similar_holdings:
                suspicious_patterns.append('Similar holding patterns detected')

        # Check for unusual circulating supply ratio
        total_supply = float(supply_data.get('totalSupply', 0))
        circulating_supply = float(supply_data.get('circulatingSupply', 0))
        if total_supply > 0:
            circulation_ratio = circulating_supply / total_supply
            if circulation_ratio < 0.1:  # Less than 10% circulating
                suspicious_patterns.append('Low circulation ratio')

        # If any suspicious patterns are found, consider it bundled
        return len(suspicious_patterns) > 0

    def _save_blacklist_update(self, deployer_address: str):
        """Save updated blacklist to config file"""
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
            
            if deployer_address not in config['blacklisted_deployers']:
                config['blacklisted_deployers'].append(deployer_address)
                
                with open('config.json', 'w') as f:
                    json.dump(config, f, indent=4)
                
                logging.info(f"Added deployer {deployer_address} to blacklist")
        except Exception as e:
            logging.error(f"Error updating blacklist: {e}")

    def check_suspicious_patterns(self, pair_data):
        """Check for suspicious patterns in trading data."""
        patterns = self.config['suspicious_patterns']
        suspicious_flags = []

        # Check for abnormal tax
        if 'priceChange' in pair_data:
            price_impact = abs(float(pair_data['priceChange'].get('h1', 0)))
            if price_impact > patterns.get('max_tax_percentage', 10):
                suspicious_flags.append(f"High price impact: {price_impact}%")

        # Check trading patterns
        if 'txns' in pair_data:
            h24_txns = pair_data['txns']['h24']
            if h24_txns['sells'] == 0 and h24_txns['buys'] > 0:
                suspicious_flags.append("Possible honeypot: no sell transactions")

        return suspicious_flags

    def get_pair_data(self, pair_address):
        """Fetch data for a specific trading pair."""
        try:
            response = requests.get(
                f"{self.base_url}",
                params={'q': pair_address},
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()

            # Filter and analyze each pair
            filtered_pairs = []
            for pair in data.get('pairs', []):
                if (not self.is_token_blacklisted(pair['baseToken']['address']) and
                    not self.is_token_blacklisted(pair['quoteToken']['address']) and
                    self.passes_filters(pair)):
                    
                    # Add suspicious pattern analysis
                    suspicious_flags = self.check_suspicious_patterns(pair)
                    if suspicious_flags:
                        pair['suspicious_flags'] = suspicious_flags
                    
                    filtered_pairs.append(pair)
            
            data['pairs'] = filtered_pairs
            return data
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching pair data: {e}")
            return None

    def analyze_price_movement(self, pair_data, timeframe_hours=24):
        """Analyze price movements to detect significant changes."""
        try:
            if not pair_data['pairs']:
                logging.info("No pairs passed the filters")
                return None

            price_data = pair_data['pairs'][0]
            current_price = float(price_data['priceUsd'])
            price_change = float(price_data['priceChange']['h24'])
            
            analysis = {
                'timestamp': datetime.now().isoformat(),
                'pair_address': price_data['pairAddress'],
                'token_name': price_data['baseToken']['name'],
                'current_price': current_price,
                'price_change_24h': price_change,
                'volume_24h': price_data['volume']['h24'],
                'liquidity_usd': price_data['liquidity']['usd'],
                'event_type': self._categorize_event(price_change, price_data)
            }

            if 'suspicious_flags' in price_data:
                analysis['suspicious_flags'] = price_data['suspicious_flags']
            
            if 'volume_analysis' in price_data:
                analysis['volume_analysis'] = price_data['volume_analysis']
            
            if 'rugcheck_analysis' in price_data:
                analysis['rugcheck_analysis'] = price_data['rugcheck_analysis']
            
            self._save_analysis(analysis)
            return analysis
            
        except (KeyError, ValueError) as e:
            logging.error(f"Error analyzing price movement: {e}")
            return None

    def _categorize_event(self, price_change, price_data):
        """Categorize the type of event based on various indicators."""
        liquidity = float(price_data['liquidity']['usd'])
        volume = float(price_data['volume']['h24'])
        
        if price_change <= -90:
            return 'potential_rug'
        elif price_change >= 100 and volume > 100000:
            return 'significant_pump'
        elif liquidity > 1000000 and volume > 500000:
            return 'high_liquidity_volume'
        elif 'cex' in price_data.get('labels', []):
            return 'cex_listed'
        elif 'suspicious_flags' in price_data:
            return 'suspicious_activity'
        else:
            return 'normal_trading'

    def _save_analysis(self, analysis):
        """Save analysis results to a file."""
        try:
            with open('analysis_results.jsonl', 'a') as f:
                json.dump(analysis, f)
                f.write('\n')
        except IOError as e:
            logging.error(f"Error saving analysis: {e}")

    def generate_report(self, days=7):
        """Generate a summary report of recent analyses."""
        try:
            df = pd.read_json('analysis_results.jsonl', lines=True)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            recent_df = df[df['timestamp'] > datetime.now() - timedelta(days=days)]
            
            report = {
                'total_pairs_analyzed': len(recent_df),
                'potential_rugs': len(recent_df[recent_df['event_type'] == 'potential_rug']),
                'significant_pumps': len(recent_df[recent_df['event_type'] == 'significant_pump']),
                'cex_listings': len(recent_df[recent_df['event_type'] == 'cex_listed']),
                'high_activity_pairs': len(recent_df[recent_df['event_type'] == 'high_liquidity_volume']),
                'suspicious_activities': len(recent_df[recent_df['event_type'] == 'suspicious_activity']),
                'average_price_change': recent_df['price_change_24h'].mean()
            }
            
            return report
        except Exception as e:
            logging.error(f"Error generating report: {e}")
            return None

async def main():
    print("Starting DexAnalyzer...")
    analyzer = DexAnalyzer()
    
    # Using WETH-USDC pair on Uniswap V2
    pair_address = "0xb4e16d0168e52d35cacd2c6185b44281ec28c9dc"
    print(f"Fetching data for pair: {pair_address}")
    pair_data = analyzer.get_pair_data(pair_address)
    
    if pair_data:
        print("Got pair data:", json.dumps(pair_data, indent=2))
        analysis = analyzer.analyze_price_movement(pair_data)
        if analysis:
            print(f"Analysis results for {analysis['token_name']}:")
            print(json.dumps(analysis, indent=2))
            
            # Execute trade if conditions are met
            if analysis['event_type'] == 'high_liquidity_volume':
                await analyzer.execute_trade(pair_data['pairs'][0], 'buy')
            
        report = analyzer.generate_report()
        if report:
            print("\nWeekly Summary Report:")
            print(json.dumps(report, indent=2))
    else:
        print("Failed to get pair data")

if __name__ == "__main__":
    asyncio.run(main())