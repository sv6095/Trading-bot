# trading_bot.py
import os
import sys
import time
import threading
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from binance import Client
from binance.exceptions import BinanceAPIException
from dotenv import load_dotenv
from colorama import Fore, Style, init
from tabulate import tabulate

init(autoreset=True)
load_dotenv()

@dataclass
class OrderResult:
    order_id: int
    symbol: str
    side: str
    quantity: float
    price: Optional[float]
    status: str
    timestamp: datetime
    order_type: str

class TradingBot:
    def __init__(self, api_key=None, api_secret=None, testnet=True):
        self.api_key = api_key or os.getenv('BINANCE_API_KEY')
        self.api_secret = api_secret or os.getenv('BINANCE_API_SECRET')
        self.testnet = testnet if testnet is not None else os.getenv('BINANCE_TESTNET', 'true').lower() == 'true'
        
        if not self.api_key or not self.api_secret:
            raise ValueError("API credentials not found")
        
        self.setup_logging()
        self.client = Client(self.api_key, self.api_secret, testnet=self.testnet)
        self.order_history = []
        self.twap_jobs = {}
        self.oco_orders = {}
        self.validate_connection()
        
    def setup_logging(self):
        os.makedirs('logs', exist_ok=True)
    
        # Configure root logger
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/trading_bot.log', mode='a'),
                logging.StreamHandler(sys.stdout)
            ],
            force=True  # This forces reconfiguration
        )
    
        self.logger = logging.getLogger("TradingBot")
        self.logger.info("Logger initialized")

        
    def validate_connection(self):
        try:
            account = self.client.futures_account()
            self.logger.info("Connected to Binance Futures Testnet")
            self.logger.info(f"Account Balance: {account.get('totalWalletBalance', 0)} USDT")
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            raise
            
    def place_market_order(self, symbol, side, quantity):
        try:
            self.logger.info(f"Placing MARKET order: {side} {quantity} {symbol}")
            
            order = self.client.futures_create_order(
                symbol=symbol, side=side.upper(), type='MARKET', quantity=str(quantity)
            )
            
            execution_price = float(order.get('avgPrice') or 0)
            self.logger.info(f"Order submitted - ID: {order['orderId']}, Status: {order['status']}")
            
            result = OrderResult(
                order_id=order['orderId'], symbol=order['symbol'], side=order['side'],
                quantity=float(order['origQty']), price=execution_price, status=order['status'],
                timestamp=datetime.now(), order_type='MARKET'
            )
            
            self.order_history.append(result)
            return result
            
        except BinanceAPIException as e:
            self.logger.error(f"API Error: {e.code} - {e.message}")
            raise
        except Exception as e:
            self.logger.error(f"Error: {e}")
            raise

    def monitor_order_execution(self, symbol, order_id, max_wait_seconds=30):
        start_time = time.time()
        
        while time.time() - start_time < max_wait_seconds:
            try:
                order = self.client.futures_get_order(symbol=symbol, orderId=order_id)
                status = order['status']
                executed_qty = float(order['executedQty'])
                avg_price = float(order.get('avgPrice') or 0)
                
                if status == 'FILLED':
                    total_cost = executed_qty * avg_price
                    print(f"Order FILLED - Price: {avg_price} USDT, Quantity: {executed_qty}, Cost: {total_cost:.4f} USDT")
                    return order
                elif status == 'PARTIALLY_FILLED':
                    remaining = float(order['origQty']) - executed_qty
                    print(f"Partially filled: {executed_qty}/{order['origQty']} (Remaining: {remaining})")
                elif status == 'NEW':
                    print("Order pending execution...")
                    
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")
                break
        
        try:
            final_order = self.client.futures_get_order(symbol=symbol, orderId=order_id)
            print(f"Monitoring timeout - Final status: {final_order['status']}")
            return final_order
        except:
            return {'orderId': order_id, 'status': 'UNKNOWN'}

    def place_market_order_with_monitoring(self, symbol, side, quantity):
        try:
            self.logger.info(f"Placing MARKET order with monitoring: {side} {quantity} {symbol}")
            
            order = self.client.futures_create_order(
                symbol=symbol, side=side.upper(), type='MARKET', quantity=str(quantity)
            )
            
            print("Monitoring order execution...")
            final_order = self.monitor_order_execution(symbol, order['orderId'])
            
            result = OrderResult(
                order_id=final_order['orderId'], symbol=final_order['symbol'], side=final_order['side'],
                quantity=float(final_order['origQty']), price=float(final_order.get('avgPrice') or 0),
                status=final_order['status'], timestamp=datetime.now(), order_type='MARKET'
            )
            
            self.order_history.append(result)
            return result
            
        except Exception as e:
            self.logger.error(f"Error: {e}")
            raise

    def place_limit_order(self, symbol, side, quantity, price):
        try:
            self.logger.info(f"Placing LIMIT order: {side} {quantity} {symbol} @ {price}")
            
            order = self.client.futures_create_order(
                symbol=symbol, side=side.upper(), type='LIMIT', timeInForce='GTC',
                quantity=str(quantity), price=str(price)
            )
            
            result = OrderResult(
                order_id=order['orderId'], symbol=order['symbol'], side=order['side'],
                quantity=float(order['origQty']), price=float(order['price']), status=order['status'],
                timestamp=datetime.now(), order_type='LIMIT'
            )
            
            self.order_history.append(result)
            return result
            
        except BinanceAPIException as e:
            self.logger.error(f"API Error: {e.code} - {e.message}")
            raise
            
    def place_stop_limit_order(self, symbol, side, quantity, price, stop_price):
        try:
            self.logger.info(f"Placing STOP-LIMIT order: {side} {quantity} {symbol}")
            
            order = self.client.futures_create_order(
                symbol=symbol, side=side.upper(), type='STOP', timeInForce='GTC',
                quantity=str(quantity), price=str(price), stopPrice=str(stop_price)
            )
            
            result = OrderResult(
                order_id=order['orderId'], symbol=order['symbol'], side=order['side'],
                quantity=float(order['origQty']), price=float(order['price']), status=order['status'],
                timestamp=datetime.now(), order_type='STOP_LIMIT'
            )
            
            self.order_history.append(result)
            return result
            
        except BinanceAPIException as e:
            self.logger.error(f"API Error: {e.code} - {e.message}")
            raise
            
    def start_twap_order(self, symbol, side, total_quantity, duration_minutes, interval_minutes=1):
        if duration_minutes <= 0 or interval_minutes <= 0:
            raise ValueError("Duration and interval must be positive")
            
        job_id = f"TWAP_{int(time.time())}"
        parts = duration_minutes // interval_minutes
        qty_per_part = total_quantity / parts
        
        job = {
            'id': job_id, 'symbol': symbol, 'side': side, 'total_quantity': total_quantity,
            'parts': parts, 'qty_per_part': qty_per_part, 'completed': 0, 'status': 'RUNNING',
            'start_time': datetime.now(), 'orders': []
        }
        
        self.twap_jobs[job_id] = job
        self.logger.info(f"Starting TWAP order {job_id}")
        
        def execute_twap():
            try:
                for i in range(parts):
                    if job['status'] != 'RUNNING':
                        break
                    order = self.place_market_order(symbol, side, qty_per_part)
                    job['orders'].append(order)
                    job['completed'] += 1
                    self.logger.info(f"TWAP {job_id}: Completed {job['completed']}/{parts}")
                    if i < parts - 1:
                        time.sleep(interval_minutes * 60)
                job['status'] = 'COMPLETED'
            except Exception as e:
                job['status'] = 'FAILED'
                job['error'] = str(e)
                
        threading.Thread(target=execute_twap, daemon=True).start()
        return job_id
        
    def place_oco_order(self, symbol, side, quantity, limit_price, stop_price, stop_limit_price):
        try:
            limit_order = self.place_limit_order(symbol, side, quantity, limit_price)
            stop_order = self.place_stop_limit_order(symbol, side, quantity, stop_limit_price, stop_price)
            
            oco_id = f"OCO_{int(time.time())}"
            oco_data = {
                'id': oco_id, 'symbol': symbol, 'side': side, 'quantity': quantity,
                'limit_order': limit_order, 'stop_order': stop_order, 'status': 'ACTIVE',
                'timestamp': datetime.now()
            }
            self.oco_orders[oco_id] = oco_data
            
            def monitor_oco():
                while oco_data['status'] == 'ACTIVE':
                    try:
                        limit_status = self.client.futures_get_order(symbol=symbol, orderId=limit_order.order_id)
                        stop_status = self.client.futures_get_order(symbol=symbol, orderId=stop_order.order_id)
                        
                        if limit_status['status'] == 'FILLED':
                            self.client.futures_cancel_order(symbol=symbol, orderId=stop_order.order_id)
                            oco_data['status'] = 'LIMIT_FILLED'
                            break
                        elif stop_status['status'] == 'FILLED':
                            self.client.futures_cancel_order(symbol=symbol, orderId=limit_order.order_id)
                            oco_data['status'] = 'STOP_FILLED'
                            break
                        time.sleep(5)
                    except Exception as e:
                        self.logger.error(f"OCO monitoring error: {e}")
                        break
                        
            threading.Thread(target=monitor_oco, daemon=True).start()
            return oco_id
        except Exception as e:
            self.logger.error(f"OCO order failed: {e}")
            raise
            
    def get_balance(self):
        try:
            account = self.client.futures_account()
            return {
                'wallet': float(account.get('totalWalletBalance', 0)),
                'available': float(account.get('availableBalance', 0)),
                'margin': float(account.get('totalMarginBalance', 0))
            }
        except Exception as e:
            self.logger.error(f"Error getting balance: {e}")
            raise
            
    def get_current_price(self, symbol):
        try:
            ticker = self.client.futures_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            self.logger.error(f"Error getting price: {e}")
            raise

    def get_live_price_stream(self, symbol, duration_seconds=10):
        print(f"Live price for {symbol} (showing for {duration_seconds} seconds):")
        start_time = time.time()
        while time.time() - start_time < duration_seconds:
            try:
                price = self.get_current_price(symbol)
                timestamp = datetime.now().strftime('%H:%M:%S')
                print(f"{timestamp} - {symbol}: {price} USDT", end='\r')
                time.sleep(0.5)
            except Exception as e:
                print(f"Error: {e}")
                break
        print()

class CLI:
    def __init__(self, bot):
        self.bot = bot
        
    def print_header(self):
        print(f"\n{Fore.CYAN}BINANCE FUTURES TRADING BOT")
        print(f"{Fore.CYAN}Connected to Testnet{Style.RESET_ALL}\n")
        
    def print_menu(self):
        print(f"\n{Fore.YELLOW}TRADING MENU{Style.RESET_ALL}")
        print(f"{Fore.GREEN}1.{Style.RESET_ALL} Place Market Order (with monitoring)")
        print(f"{Fore.GREEN}2.{Style.RESET_ALL} Place Limit Order")
        print(f"{Fore.GREEN}3.{Style.RESET_ALL} Place Stop-Limit Order")
        print(f"{Fore.GREEN}4.{Style.RESET_ALL} Start TWAP Order")
        print(f"{Fore.GREEN}5.{Style.RESET_ALL} Place OCO Order")
        print(f"{Fore.BLUE}6.{Style.RESET_ALL} Check Account Balance")
        print(f"{Fore.BLUE}7.{Style.RESET_ALL} Get Current Price")
        print(f"{Fore.BLUE}8.{Style.RESET_ALL} View Live Price Stream")
        print(f"{Fore.BLUE}9.{Style.RESET_ALL} View Order History")
        print(f"{Fore.BLUE}10.{Style.RESET_ALL} Check TWAP Status")
        print(f"{Fore.BLUE}11.{Style.RESET_ALL} Check OCO Status")
        print(f"{Fore.RED}12.{Style.RESET_ALL} Exit")
        
    def get_user_input(self, prompt, input_type=str):
        while True:
            try:
                value = input(f"{Fore.CYAN}{prompt}{Style.RESET_ALL}")
                return value.strip().upper() if input_type == str else input_type(value)
            except ValueError:
                print(f"{Fore.RED}Invalid input. Expected {input_type.__name__}.{Style.RESET_ALL}")
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Operation cancelled.{Style.RESET_ALL}")
                return None
                
    def display_order_result(self, order):
        print(f"\n{Fore.GREEN}ORDER EXECUTED SUCCESSFULLY{Style.RESET_ALL}")
        order_data = [
            ['Order ID', order.order_id], ['Symbol', order.symbol], ['Side', order.side],
            ['Quantity', order.quantity], ['Price', order.price if order.price else 'Market'],
            ['Status', order.status], ['Type', order.order_type],
            ['Timestamp', order.timestamp.strftime('%Y-%m-%d %H:%M:%S')]
        ]
        print(tabulate(order_data, headers=['Field', 'Value'], tablefmt='grid'))
        
    def display_balance(self, balance):
        print(f"\n{Fore.BLUE}ACCOUNT BALANCE{Style.RESET_ALL}")
        balance_data = [
            ['Total Wallet Balance', f"{balance['wallet']:.4f} USDT"],
            ['Available Balance', f"{balance['available']:.4f} USDT"],
            ['Total Margin Balance', f"{balance['margin']:.4f} USDT"]
        ]
        print(tabulate(balance_data, headers=['Type', 'Amount'], tablefmt='grid'))
        
    def display_order_history(self):
        if not self.bot.order_history:
            print(f"\n{Fore.YELLOW}No orders in history{Style.RESET_ALL}")
            return
            
        print(f"\n{Fore.BLUE}ORDER HISTORY{Style.RESET_ALL}")
        history_data = []
        for order in self.bot.order_history[-10:]:
            history_data.append([
                order.order_id, order.symbol, order.side, order.quantity,
                order.price if order.price else 'Market', order.status,
                order.order_type, order.timestamp.strftime('%H:%M:%S')
            ])
        headers = ['ID', 'Symbol', 'Side', 'Qty', 'Price', 'Status', 'Type', 'Time']
        print(tabulate(history_data, headers=headers, tablefmt='grid'))
        
    def run(self):
        self.print_header()
        
        while True:
            try:
                self.print_menu()
                choice = input(f"\n{Fore.CYAN}Enter your choice (1-12): {Style.RESET_ALL}").strip()
                
                if choice == '1':
                    symbol = self.get_user_input("Enter symbol (e.g., BTCUSDT): ")
                    if not symbol: continue
                    side = self.get_user_input("Enter side (BUY/SELL): ")
                    if not side: continue
                    quantity = self.get_user_input("Enter quantity: ", float)
                    if not quantity: continue
                    order = self.bot.place_market_order_with_monitoring(symbol, side, quantity)
                    self.display_order_result(order)
                    
                elif choice == '2':
                    symbol = self.get_user_input("Enter symbol: ")
                    if not symbol: continue
                    side = self.get_user_input("Enter side (BUY/SELL): ")
                    if not side: continue
                    quantity = self.get_user_input("Enter quantity: ", float)
                    if not quantity: continue
                    price = self.get_user_input("Enter price: ", float)
                    if not price: continue
                    order = self.bot.place_limit_order(symbol, side, quantity, price)
                    self.display_order_result(order)
                    
                elif choice == '3':
                    symbol = self.get_user_input("Enter symbol: ")
                    if not symbol: continue
                    side = self.get_user_input("Enter side (BUY/SELL): ")
                    if not side: continue
                    quantity = self.get_user_input("Enter quantity: ", float)
                    if not quantity: continue
                    price = self.get_user_input("Enter limit price: ", float)
                    if not price: continue
                    stop_price = self.get_user_input("Enter stop price: ", float)
                    if not stop_price: continue
                    order = self.bot.place_stop_limit_order(symbol, side, quantity, price, stop_price)
                    self.display_order_result(order)
                    
                elif choice == '4':
                    symbol = self.get_user_input("Enter symbol: ")
                    if not symbol: continue
                    side = self.get_user_input("Enter side (BUY/SELL): ")
                    if not side: continue
                    total_quantity = self.get_user_input("Enter total quantity: ", float)
                    if not total_quantity: continue
                    duration = self.get_user_input("Enter duration (minutes): ", int)
                    if not duration: continue
                    interval = self.get_user_input("Enter interval (minutes, default 1): ", int) or 1
                    job_id = self.bot.start_twap_order(symbol, side, total_quantity, duration, interval)
                    print(f"{Fore.GREEN}TWAP order started with ID: {job_id}{Style.RESET_ALL}")
                    
                elif choice == '5':
                    symbol = self.get_user_input("Enter symbol: ")
                    if not symbol: continue
                    side = self.get_user_input("Enter side (BUY/SELL): ")
                    if not side: continue
                    quantity = self.get_user_input("Enter quantity: ", float)
                    if not quantity: continue
                    limit_price = self.get_user_input("Enter limit price: ", float)
                    if not limit_price: continue
                    stop_price = self.get_user_input("Enter stop price: ", float)
                    if not stop_price: continue
                    stop_limit_price = self.get_user_input("Enter stop limit price: ", float)
                    if not stop_limit_price: continue
                    oco_id = self.bot.place_oco_order(symbol, side, quantity, limit_price, stop_price, stop_limit_price)
                    print(f"{Fore.GREEN}OCO order placed with ID: {oco_id}{Style.RESET_ALL}")
                    
                elif choice == '6':
                    balance = self.bot.get_balance()
                    self.display_balance(balance)
                    
                elif choice == '7':
                    symbol = self.get_user_input("Enter symbol: ")
                    if not symbol: continue
                    price = self.bot.get_current_price(symbol)
                    print(f"\n{Fore.BLUE}Current price of {symbol}: {price}{Style.RESET_ALL}")
                    
                elif choice == '8':
                    symbol = self.get_user_input("Enter symbol for live price: ")
                    if not symbol: continue
                    duration = self.get_user_input("Duration in seconds (default 10): ", int) or 10
                    self.bot.get_live_price_stream(symbol, duration)
                    
                elif choice == '9':
                    self.display_order_history()
                    
                elif choice == '10':
                    if not self.bot.twap_jobs:
                        print(f"{Fore.YELLOW}No TWAP orders found{Style.RESET_ALL}")
                        continue
                    print(f"\n{Fore.BLUE}TWAP ORDERS STATUS{Style.RESET_ALL}")
                    for job_id, job in self.bot.twap_jobs.items():
                        progress = (job['completed'] / job['parts']) * 100
                        print(f"ID: {job_id}")
                        print(f"Status: {job['status']}")
                        print(f"Progress: {job['completed']}/{job['parts']} ({progress:.1f}%)")
                        print("-" * 30)
                        
                elif choice == '11':
                    if not self.bot.oco_orders:
                        print(f"{Fore.YELLOW}No OCO orders found{Style.RESET_ALL}")
                        continue
                    print(f"\n{Fore.BLUE}OCO ORDERS STATUS{Style.RESET_ALL}")
                    for oco_id, oco in self.bot.oco_orders.items():
                        print(f"ID: {oco_id}")
                        print(f"Symbol: {oco['symbol']}")
                        print(f"Status: {oco['status']}")
                        print(f"Limit Order ID: {oco['limit_order'].order_id}")
                        print(f"Stop Order ID: {oco['stop_order'].order_id}")
                        print("-" * 30)
                        
                elif choice == '12':
                    print(f"\n{Fore.YELLOW}Exiting trading bot...{Style.RESET_ALL}")
                    break
                    
                else:
                    print(f"{Fore.RED}Invalid choice. Please try again.{Style.RESET_ALL}")
                    
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Exiting...{Style.RESET_ALL}")
                break
            except Exception as e:
                print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")

def main():
    try:
        bot = TradingBot()
        cli = CLI(bot)
        cli.run()
    except Exception as e:
        print(f"Failed to initialize bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
