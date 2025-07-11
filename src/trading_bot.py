import os
import sys
import logging
from binance import Client
from dotenv import load_dotenv
import time
from datetime import datetime
from .market_orders import MarketOrderHandler
from .limit_orders import LimitOrderHandler
from .advanced.oco import OCOOrderHandler
from .advanced.twap import TWAPOrderHandler
from .advanced.grid import GridOrderHandler

load_dotenv()

class TradingBot:
    def get_order_history(self, symbol=None, limit=10):
        """
        Fetch order history from Binance Futures API.
        Returns a list of order objects (dicts).
        """
        try:
            if symbol:
                # Validate symbol exists in futures market
                try:
                    self.client.futures_symbol_ticker(symbol=symbol)
                except Exception:
                    self.logger.error(f"Symbol {symbol} not found in futures market")
                    return []
                orders = self.client.futures_get_all_orders(symbol=symbol, limit=limit)
            else:
                # Get futures exchange info instead of spot
                exchange_info = self.client.futures_exchange_info()
                # Filter for active USDT perpetual contracts
                symbols = [
                    s['symbol'] for s in exchange_info['symbols'] 
                    if (s['quoteAsset'] == 'USDT' and 
                        s['status'] == 'TRADING' and
                        s['contractType'] == 'PERPETUAL')
                ]
                orders = []
                processed_symbols = 0
                max_symbols = 10  # Limit to prevent rate limiting
                for sym in symbols[:max_symbols]:
                    try:
                        sym_orders = self.client.futures_get_all_orders(
                            symbol=sym, 
                            limit=min(limit, 100)  # Limit per symbol
                        )
                        orders.extend(sym_orders)
                        processed_symbols += 1
                        # Add small delay to avoid rate limiting
                        time.sleep(0.1)
                    except Exception as e:
                        self.logger.warning(f"Skipping symbol {sym}: {e}")
                        continue
                self.logger.info(f"Processed {processed_symbols} symbols")
            # Sort by update time and limit results
            orders = sorted(orders, key=lambda o: o.get('updateTime', 0), reverse=True)
            orders = orders[:limit]
            class OrderObj:
                def __init__(self, d):
                    for k, v in d.items():
                        setattr(self, k, v)
                    # Safe attribute access with proper defaults
                    self.timestamp = (
                        datetime.fromtimestamp(self.updateTime / 1000) 
                        if hasattr(self, 'updateTime') and self.updateTime 
                        else None
                    )
                    self.order_id = getattr(self, 'orderId', None)
                    # Handle price conversion safely
                    price_val = getattr(self, 'price', '0')
                    self.price = float(price_val) if price_val and price_val != '0' else None
                    # Handle quantity conversion safely
                    qty_val = getattr(self, 'origQty', '0')
                    self.quantity = float(qty_val) if qty_val and qty_val != '0' else None
                    self.status = getattr(self, 'status', 'Unknown')
                    self.side = getattr(self, 'side', 'Unknown')
                    self.symbol = getattr(self, 'symbol', 'Unknown')
                    self.order_type = getattr(self, 'type', 'Unknown')
                    # Additional futures-specific fields
                    self.position_side = getattr(self, 'positionSide', 'BOTH')
                    self.reduce_only = getattr(self, 'reduceOnly', False)
                    self.close_position = getattr(self, 'closePosition', False)
            return [OrderObj(o) for o in orders]
        except Exception as e:
            self.logger.error(f"Error fetching order history: {e}")
            return []
    def __init__(self):
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.api_secret = os.getenv('BINANCE_API_SECRET')
        self.testnet = os.getenv('BINANCE_TESTNET', 'true').lower() == 'true'
        
        if not self.api_key or not self.api_secret:
            raise ValueError("API credentials not found")
        
        self._setup_logging()
        self.client = Client(self.api_key, self.api_secret, testnet=self.testnet)
        self.order_history = []
        
        # Initialize handlers
        self.market_orders = MarketOrderHandler(self.client)
        self.limit_orders = LimitOrderHandler(self.client)
        self.oco_orders = OCOOrderHandler(self.client, self.limit_orders)
        self.twap_orders = TWAPOrderHandler(self.market_orders)
        self.grid_orders = GridOrderHandler(self.client, self.limit_orders)
        
        self._validate_connection()
    
    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('bot.log', mode='a'),
                logging.StreamHandler(sys.stdout)
            ],
            force=True
        )
        self.logger = logging.getLogger("TradingBot")
    
    def _validate_connection(self):
        try:
            self.client.futures_account()  # Test API connection
            self.logger.info(f"Connected to Binance {'Testnet' if self.testnet else 'Live'}")
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            raise
    
    def get_balance(self):
        """Get futures account balance for all assets"""
        balance = self.client.futures_account_balance()
        balances = {}
        for asset in balance:
            balances[asset['asset']] = {
                'available': float(asset['availableBalance']),
                'wallet': float(asset['balance'])
            }
        return balances
    
    def get_current_price(self, symbol: str) -> float:
        """Get real-time price directly from the exchange"""
        ticker = self.client.futures_symbol_ticker(symbol=symbol)
        return float(ticker['price'])
    
    def monitor_price(self, symbol: str, duration: int = 0, callback=None):
        """Monitor price continuously with optional duration in seconds"""
        start_time = time.time()
        try:
            while True:
                price = self.get_current_price(symbol)
                timestamp = datetime.now().strftime('%H:%M:%S')
                
                if callback:
                    callback(symbol, price, timestamp)
                
                if duration and (time.time() - start_time) >= duration:
                    break
                    
                time.sleep(1)  # 1 second delay between updates
                
        except KeyboardInterrupt:
            return
    
    def get_symbol_info(self, symbol):
        """
        Get symbol information using python-binance library
        """
        try:
            # Get exchange info
            exchange_info = self.client.get_exchange_info()
            
            # Find the specific symbol
            symbol_info = None
            for s in exchange_info['symbols']:
                if s['symbol'] == symbol:
                    symbol_info = s
                    break
            
            if not symbol_info:
                raise Exception(f"Symbol {symbol} not found")
            
            # Extract precision and filter data
            symbol_data = {
                'symbol': symbol,
                'status': symbol_info['status'],
                'base_asset': symbol_info['baseAsset'],
                'quote_asset': symbol_info['quoteAsset'],
                'price_precision': symbol_info.get('quotePrecision', 8),
                'quantity_precision': symbol_info.get('baseAssetPrecision', 8),
                'min_quantity': 0,
                'max_quantity': None,
                'step_size': 0,
                'min_price': 0,
                'max_price': None,
                'tick_size': 0
            }
            
            # Parse filters
            for filter_info in symbol_info['filters']:
                filter_type = filter_info['filterType']
                
                if filter_type == 'LOT_SIZE':
                    symbol_data['min_quantity'] = float(filter_info['minQty'])
                    symbol_data['max_quantity'] = float(filter_info['maxQty']) if filter_info['maxQty'] != '0' else None
                    symbol_data['step_size'] = float(filter_info['stepSize'])
                    
                elif filter_type == 'PRICE_FILTER':
                    symbol_data['min_price'] = float(filter_info['minPrice'])
                    symbol_data['max_price'] = float(filter_info['maxPrice']) if filter_info['maxPrice'] != '0' else None
                    symbol_data['tick_size'] = float(filter_info['tickSize'])
            
            return symbol_data
            
        except Exception as e:
            raise Exception(f"Error fetching symbol info for {symbol}: {str(e)}")
