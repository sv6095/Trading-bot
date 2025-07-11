import time
import threading
import logging
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class GridLevel:
    price: float
    quantity: float
    side: str
    order_id: int = None
    status: str = 'PENDING'

class GridOrderHandler:
    def __init__(self, client, limit_order_handler):
        self.client = client
        self.limit_order_handler = limit_order_handler
        self.logger = logging.getLogger("GridOrder")
        self.grid_strategies = {}
    
    def create_grid_strategy(self, symbol: str, lower_price: float, upper_price: float, 
                           grid_count: int, total_quantity: float) -> str:
        if grid_count < 2:
            raise ValueError("Grid count must be at least 2")
        if lower_price >= upper_price:
            raise ValueError("Lower price must be less than upper price")
        
        grid_id = f"GRID_{int(time.time())}"
        price_step = (upper_price - lower_price) / (grid_count - 1)
        quantity_per_level = total_quantity / grid_count
        
        grid_levels = []
        for i in range(grid_count):
            price = lower_price + (i * price_step)
            side = 'BUY' if i < grid_count // 2 else 'SELL'
            
            grid_levels.append(GridLevel(
                price=price,
                quantity=quantity_per_level,
                side=side
            ))
        
        strategy = {
            'id': grid_id,
            'symbol': symbol,
            'grid_levels': grid_levels,
            'status': 'CREATED',
            'created_time': datetime.now(),
            'active_orders': 0,
            'total_trades': 0,
            'profit_loss': 0.0
        }
        
        self.grid_strategies[grid_id] = strategy
        return grid_id
    
    def start_grid_strategy(self, grid_id: str) -> bool:
        if grid_id not in self.grid_strategies:
            return False
        
        strategy = self.grid_strategies[grid_id]
        current_price = self._get_current_price(strategy['symbol'])
        
        # Place initial orders
        for level in strategy['grid_levels']:
            if ((level.side == 'BUY' and level.price < current_price) or 
                (level.side == 'SELL' and level.price > current_price)):
                
                try:
                    order = self.limit_order_handler.place_order(
                        strategy['symbol'], level.side, level.quantity, level.price
                    )
                    level.order_id = order.order_id
                    level.status = 'PLACED'
                    strategy['active_orders'] += 1
                except Exception as e:
                    self.logger.error(f"Grid order placement error: {e}")
        
        strategy['status'] = 'RUNNING'
        self._start_monitoring(grid_id)
        return True
    
    def _start_monitoring(self, grid_id: str):
        threading.Thread(target=self._monitor_grid, args=(grid_id,), daemon=True).start()
    
    def _monitor_grid(self, grid_id: str):
        strategy = self.grid_strategies[grid_id]
        
        while strategy['status'] == 'RUNNING':
            try:
                for level in strategy['grid_levels']:
                    if level.status == 'PLACED' and level.order_id:
                        order_status = self.client.futures_get_order(
                            symbol=strategy['symbol'], orderId=level.order_id
                        )
                        
                        if order_status['status'] == 'FILLED':
                            level.status = 'FILLED'
                            strategy['active_orders'] -= 1
                            strategy['total_trades'] += 1
                            
                            # Update P&L
                            if level.side == 'SELL':
                                strategy['profit_loss'] += level.quantity * level.price
                            else:
                                strategy['profit_loss'] -= level.quantity * level.price
                
                time.sleep(5)
                
            except Exception as e:
                self.logger.error(f"Grid monitoring error: {e}")
                break
    
    def stop_grid_strategy(self, grid_id: str) -> bool:
        if grid_id not in self.grid_strategies:
            return False
        
        strategy = self.grid_strategies[grid_id]
        
        # Cancel all active orders
        for level in strategy['grid_levels']:
            if level.status == 'PLACED' and level.order_id:
                self.limit_order_handler.cancel_order(strategy['symbol'], level.order_id)
                level.status = 'CANCELLED'
        
        strategy['status'] = 'STOPPED'
        strategy['active_orders'] = 0
        return True
    
    def get_grid_strategies(self) -> Dict[str, Dict[str, Any]]:
        return self.grid_strategies
    
    def _get_current_price(self, symbol: str) -> float:
        ticker = self.client.futures_symbol_ticker(symbol=symbol)
        return float(ticker['price'])
