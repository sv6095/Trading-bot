import logging
import time
from datetime import datetime
from .order_result import OrderResult

class MarketOrderHandler:
    def __init__(self, client):
        self.client = client
        self.logger = logging.getLogger("MarketOrder")
        self._initial_price = 0
    
    def _get_current_price(self, symbol: str) -> float:
        ticker = self.client.futures_symbol_ticker(symbol=symbol)
        return float(ticker['price'])

    def place_order(self, symbol: str, side: str, quantity: float) -> OrderResult:
        try:
            # Get initial price before order execution
            self._initial_price = self._get_current_price(symbol)
            
            self.logger.info(f"Placing MARKET order: {side} {quantity} {symbol}")
        
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side.upper(),
                type='MARKET',
                quantity=str(quantity)
            )
        
            # Wait briefly for order to be processed
            time.sleep(0.5)
            
            # Fetch the complete order details to get accurate status and price
            order_details = self.client.futures_get_order(
                symbol=symbol,
                orderId=order['orderId']
            )
            
            execution_price = float(order_details.get('avgPrice', 0))
            if execution_price == 0:
                execution_price = float(order_details.get('price', 0))
            
            self.logger.info(f"Market order executed at price: {execution_price}")

            # Validate prices and calculate price change
            if self._initial_price > 0 and execution_price > 0:
                # For SELL orders, positive change means price went down
                multiplier = -1 if side.upper() == 'SELL' else 1
                price_change = multiplier * ((execution_price - self._initial_price) / self._initial_price) * 100
                self.logger.info(f"Price change from {self._initial_price} to {execution_price}: {price_change:.2f}%")
            else:
                self.logger.warning("Could not calculate price change - invalid prices")
            
            return OrderResult(
                order_id=order_details['orderId'],
                symbol=order_details['symbol'],
                side=order_details['side'],
                quantity=float(order_details['origQty']),
                price=execution_price,
                status=order_details['status'],
                timestamp=datetime.now(),
                order_type='MARKET'
            )
        
        except Exception as e:
            self.logger.error(f"Market order error: {e}")
            raise

