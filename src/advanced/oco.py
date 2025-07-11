import time
import threading
import logging
from datetime import datetime
from typing import Dict, Any

class OCOOrderHandler:
    def __init__(self, client, limit_order_handler):
        self.client = client
        self.limit_order_handler = limit_order_handler
        self.logger = logging.getLogger("OCOOrder")
        self.oco_orders = {}
    
    def place_oco_order(self, symbol: str, side: str, quantity: float, 
                       limit_price: float, stop_price: float, stop_limit_price: float) -> str:
        try:
            # Place both orders
            limit_order = self.limit_order_handler.place_order(symbol, side, quantity, limit_price)
            stop_order = self.limit_order_handler.place_stop_limit_order(
                symbol, side, quantity, stop_limit_price, stop_price
            )
            
            oco_id = f"OCO_{int(time.time())}"
            oco_data = {
                'id': oco_id,
                'symbol': symbol,
                'limit_order': limit_order,
                'stop_order': stop_order,
                'status': 'ACTIVE',
                'timestamp': datetime.now()
            }
            
            self.oco_orders[oco_id] = oco_data
            self._start_monitoring(oco_data)
            
            return oco_id
            
        except Exception as e:
            self.logger.error(f"OCO order error: {e}")
            raise
    
    def _start_monitoring(self, oco_data: Dict[str, Any]):
        threading.Thread(target=self._monitor_oco, args=(oco_data,), daemon=True).start()
    
    def _monitor_oco(self, oco_data: Dict[str, Any]):
        while oco_data['status'] == 'ACTIVE':
            try:
                symbol = oco_data['symbol']
                limit_order = oco_data['limit_order']
                stop_order = oco_data['stop_order']
                
                limit_status = self.client.futures_get_order(symbol=symbol, orderId=limit_order.order_id)
                stop_status = self.client.futures_get_order(symbol=symbol, orderId=stop_order.order_id)
                
                if limit_status['status'] == 'FILLED':
                    self.limit_order_handler.cancel_order(symbol, stop_order.order_id)
                    oco_data['status'] = 'LIMIT_FILLED'
                    break
                elif stop_status['status'] == 'FILLED':
                    self.limit_order_handler.cancel_order(symbol, limit_order.order_id)
                    oco_data['status'] = 'STOP_FILLED'
                    break
                    
                time.sleep(5)
                
            except Exception as e:
                self.logger.error(f"OCO monitoring error: {e}")
                break
    
    def get_oco_orders(self) -> Dict[str, Dict[str, Any]]:
        return self.oco_orders
