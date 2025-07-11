import logging
import time
from datetime import datetime
from .order_result import OrderResult


class LimitOrderHandler:
    def __init__(self, client):
        self.client = client
        self.logger = logging.getLogger("LimitOrder")
        self._price_precision_cache = {}
    
    def _get_symbol_price_precision(self, symbol: str) -> int:
        if symbol not in self._price_precision_cache:
            try:
                info = self.client.futures_exchange_info()
                for s in info['symbols']:
                    if s['symbol'] == symbol:
                        self._price_precision_cache[symbol] = len(s['filters'][0]['tickSize'].rstrip('0').split('.')[1])
                        break
            except Exception as e:
                self.logger.warning(f"Could not get price precision for {symbol}: {e}")
                return 1  # Default to 1 decimal place if we can't get the info
        return self._price_precision_cache[symbol]
    
    def _format_price(self, symbol: str, price: float) -> float:
        """Format price according to symbol's precision requirements"""
        precision = self._get_symbol_price_precision(symbol)
        return round(price, precision)

    def place_order(self, symbol: str, side: str, quantity: float, price: float) -> OrderResult:
        try:
            current_price = self._get_current_price(symbol)
            formatted_price = self._format_price(symbol, price)
            self._log_execution_prediction(side, formatted_price, current_price)
            
            self.logger.info(f"Placing LIMIT order: {side} {quantity} {symbol} @ {formatted_price}")
            
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side.upper(),
                type='LIMIT',
                timeInForce='GTC',
                quantity=str(quantity),
                price=str(formatted_price)
            )
            
            # Get actual execution price for immediate fills
            actual_price = self._get_execution_price(symbol, order, formatted_price, side, current_price)
            
            return OrderResult(
                order_id=order['orderId'],
                symbol=order['symbol'],
                side=order['side'],
                quantity=float(order['origQty']),
                price=actual_price,
                status=order['status'],
                timestamp=datetime.now(),
                order_type='LIMIT'
            )
            
        except Exception as e:
            self.logger.error(f"Limit order error: {e}")
            raise
    
    def place_stop_limit_order(self, symbol: str, side: str, quantity: float, 
                              price: float, stop_price: float) -> OrderResult:
        try:
            current_price = self._get_current_price(symbol)
            self._validate_stop_price(side, stop_price, current_price)
            
            self.logger.info(f"Placing STOP-LIMIT: {side} {quantity} {symbol} @ {price} (stop: {stop_price})")
            
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side.upper(),
                type='STOP',
                timeInForce='GTC',
                quantity=str(quantity),
                price=str(price),
                stopPrice=str(stop_price)
            )
            
            return OrderResult(
                order_id=order['orderId'],
                symbol=order['symbol'],
                side=order['side'],
                quantity=float(order['origQty']),
                price=float(order['price']),
                status=order['status'],
                timestamp=datetime.now(),
                order_type='STOP_LIMIT'
            )
            
        except Exception as e:
            self.logger.error(f"Stop-limit order error: {e}")
            raise
    
    def cancel_order(self, symbol: str, order_id: int) -> bool:
        try:
            self.client.futures_cancel_order(symbol=symbol, orderId=order_id)
            self.logger.info(f"Order cancelled: {order_id}")
            return True
        except Exception as e:
            self.logger.error(f"Cancel error: {e}")
            return False
    
    def _get_current_price(self, symbol: str) -> float:
        ticker = self.client.futures_symbol_ticker(symbol=symbol)
        return float(ticker['price'])
    
    def _get_execution_price(self, symbol: str, order: dict, limit_price: float, side: str, current_price: float) -> float:
        """Get actual execution price for limit orders"""
        try:
            # Check if order executed immediately
            if self._will_execute_immediately(side, limit_price, current_price):
                # Wait briefly for execution
                time.sleep(0.5)
                
                # Get order details to see actual fill price
                order_details = self.client.futures_get_order(symbol=symbol, orderId=order['orderId'])
                
                if order_details.get('status') == 'FILLED':
                    avg_price = float(order_details.get('avgPrice', 0))
                    if avg_price > 0:
                        self.logger.info(f"Order filled at actual price: {avg_price}")
                        return avg_price
            
            # Return original limit price if not immediately filled
            return float(order['price'])
            
        except Exception as e:
            self.logger.warning(f"Could not get execution price: {e}")
            return float(order['price'])
    
    def _will_execute_immediately(self, side: str, price: float, current_price: float) -> bool:
        """Check if limit order will execute immediately"""
        side = side.upper()
        if side == 'BUY':
            return price >= current_price
        else:
            return price <= current_price
    
    def _log_execution_prediction(self, side: str, price: float, current_price: float):
        side = side.upper()
        
        if side == 'BUY':
            if price >= current_price:
                self.logger.warning(f"BUY @ {price} >= current {current_price} - IMMEDIATE EXECUTION")
            else:
                self.logger.info(f"BUY @ {price} < current {current_price} - WAITING for price drop")
        else:
            if price <= current_price:
                self.logger.warning(f"SELL @ {price} <= current {current_price} - IMMEDIATE EXECUTION")
            else:
                self.logger.info(f"SELL @ {price} > current {current_price} - WAITING for price rise")
    
    def _validate_stop_price(self, side: str, stop_price: float, current_price: float):
        side = side.upper()
        
        if side == 'BUY' and stop_price <= current_price:
            raise ValueError(f"BUY stop price ({stop_price}) must be > current price ({current_price})")
        elif side == 'SELL' and stop_price >= current_price:
            raise ValueError(f"SELL stop price ({stop_price}) must be < current price ({current_price})")
