import time
import threading
import logging
from datetime import datetime
from typing import Dict, Any

class TWAPOrderHandler:
    def __init__(self, market_order_handler):
        self.market_order_handler = market_order_handler
        self.logger = logging.getLogger("TWAPOrder")
        self.twap_jobs = {}
    
    def start_twap_order(self, symbol: str, side: str, total_quantity: float, 
                        duration_minutes: int, interval_minutes: int = 1) -> str:
        if duration_minutes <= 0 or interval_minutes <= 0:
            raise ValueError("Duration and interval must be positive")
        
        job_id = f"TWAP_{int(time.time())}"
        parts = duration_minutes // interval_minutes
        qty_per_part = total_quantity / parts
        
        job = {
            'id': job_id,
            'symbol': symbol,
            'side': side,
            'total_quantity': total_quantity,
            'parts': parts,
            'qty_per_part': qty_per_part,
            'interval_minutes': interval_minutes,
            'completed': 0,
            'status': 'RUNNING',
            'start_time': datetime.now(),
            'orders': []
        }
        
        self.twap_jobs[job_id] = job
        self._start_execution(job)
        
        return job_id
    
    def _start_execution(self, job: Dict[str, Any]):
        threading.Thread(target=self._execute_twap, args=(job,), daemon=True).start()
    
    def _execute_twap(self, job: Dict[str, Any]):
        try:
            for i in range(job['parts']):
                if job['status'] != 'RUNNING':
                    break
                
                order = self.market_order_handler.place_order(
                    job['symbol'], job['side'], job['qty_per_part']
                )
                
                job['orders'].append(order)
                job['completed'] += 1
                
                if i < job['parts'] - 1:
                    time.sleep(job['interval_minutes'] * 60)
            
            job['status'] = 'COMPLETED'
            
        except Exception as e:
            job['status'] = 'FAILED'
            job['error'] = str(e)
            self.logger.error(f"TWAP error: {e}")
    
    def get_twap_jobs(self) -> Dict[str, Dict[str, Any]]:
        return self.twap_jobs
    
    def cancel_twap_job(self, job_id: str) -> bool:
        if job_id in self.twap_jobs:
            job = self.twap_jobs[job_id]
            if job['status'] == 'RUNNING':
                job['status'] = 'CANCELLED'
                return True
        return False
