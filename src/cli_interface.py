import sys
from colorama import Fore, Style, init
from tabulate import tabulate

init(autoreset=True)

class TradingCLI:
    def __init__(self, bot):
        self.bot = bot
        self.symbol_info_cache = {}
    
    def run(self):
        self._print_header()
        
        while True:
            try:
                self._print_menu()
                choice = input(f"\n{Fore.CYAN}Enter choice (1-10): {Style.RESET_ALL}").strip()
                
                if choice == '1':
                    self._handle_market_order()
                elif choice == '2':
                    self._handle_limit_order()
                elif choice == '3':
                    self._handle_oco_order()
                elif choice == '4':
                    self._handle_twap_order()
                elif choice == '5':
                    self._handle_grid_strategy()
                elif choice == '6':
                    self._handle_balance()
                elif choice == '7':
                    self._handle_price()
                elif choice == '8':
                    self._handle_order_history()
                elif choice == '9':
                    self._handle_status()
                elif choice == '10':
                    print(f"\n{Fore.YELLOW}Exiting...{Style.RESET_ALL}")
                    break
                else:
                    print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")
                    
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Exiting...{Style.RESET_ALL}")
                break
            except Exception as e:
                print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
    
    def _print_header(self):
        print(f"\n{Fore.CYAN}BINANCE TRADING BOT{Style.RESET_ALL}")
    
    def _print_menu(self):
        print(f"\n{Fore.YELLOW}MENU{Style.RESET_ALL}")
        print(f"{Fore.GREEN}1.{Style.RESET_ALL} Market Order")
        print(f"{Fore.GREEN}2.{Style.RESET_ALL} Limit Order")
        print(f"{Fore.GREEN}3.{Style.RESET_ALL} OCO Order")
        print(f"{Fore.GREEN}4.{Style.RESET_ALL} TWAP Order")
        print(f"{Fore.GREEN}5.{Style.RESET_ALL} Grid Strategy")
        print(f"{Fore.BLUE}6.{Style.RESET_ALL} Balance")
        print(f"{Fore.BLUE}7.{Style.RESET_ALL} Live Price")
        print(f"{Fore.BLUE}8.{Style.RESET_ALL} Order History")
        print(f"{Fore.BLUE}9.{Style.RESET_ALL} Status")
        print(f"{Fore.RED}10.{Style.RESET_ALL} Exit")
    
    def _get_input(self, prompt: str, input_type=str):
        try:
            value = input(f"{Fore.CYAN}{prompt}{Style.RESET_ALL}")
            if input_type == str:
                return value.strip().upper()
            else:
                return input_type(value.strip())
        except ValueError:
            print(f"{Fore.RED}Invalid input format{Style.RESET_ALL}")
            return None
        except Exception as e:
            print(f"{Fore.RED}Input error: {e}{Style.RESET_ALL}")
            return None
    
    def _get_symbol_info(self, symbol):
        """Get and cache symbol information"""
        if symbol not in self.symbol_info_cache:
            try:
                info = self.bot.get_symbol_info(symbol)
                if info:
                    self.symbol_info_cache[symbol] = info
                else:
                    print(f"{Fore.RED}No information available for {symbol}{Style.RESET_ALL}")
                    return None
            except Exception as e:
                print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
                return None
        return self.symbol_info_cache[symbol]
    
    def _format_price(self, symbol, price):
        """Format price according to symbol's precision"""
        if price is None:
            return None
        info = self._get_symbol_info(symbol)
        precision = info.get('price_precision', 8) if info else 8
        return round(float(price), precision)
    
    def _format_quantity(self, symbol, quantity):
        """Format quantity according to symbol's precision"""
        if quantity is None:
            return None
        info = self._get_symbol_info(symbol)
        precision = info.get('quantity_precision', 8) if info else 8
        return round(float(quantity), precision)
    
    def _validate_order_params(self, symbol, quantity, price=None):
        """Validate order parameters"""
        info = self._get_symbol_info(symbol)
        if not info:
            return False, "Could not fetch symbol information"
        
        if quantity < info.get('min_quantity', 0):
            return False, f"Quantity {quantity} too low"
            
        if info.get('max_quantity') and quantity > info['max_quantity']:
            return False, f"Quantity {quantity} too high"
            
        if price:
            if price < info.get('min_price', 0):
                return False, f"Price {price} too low"
            if info.get('max_price') and price > info['max_price']:
                return False, f"Price {price} too high"
                
        return True, "Valid"
    
    def _display_symbol_info(self, symbol):
        """Display trading information"""
        info = self._get_symbol_info(symbol)
        if info:
            data = [
                ['Min Quantity', info.get('min_quantity', 'N/A')],
                ['Step Size', info.get('step_size', 'N/A')],
                ['Price Precision', info.get('price_precision', 'N/A')],
                ['Qty Precision', info.get('quantity_precision', 'N/A')]
            ]
            if 'min_price' in info:
                data.append(['Min Price', info['min_price']])
            if 'max_price' in info:
                data.append(['Max Price', info['max_price']])
                
            print(f"\n{Fore.YELLOW}Symbol Information:{Style.RESET_ALL}")
            print(tabulate(data, headers=['Parameter', 'Value'], tablefmt='grid'))
    
    def _handle_market_order(self):
        symbol = self._get_input("Symbol (e.g., BTCUSDT): ")
        if not symbol: return
        
        side = self._get_input("Side (BUY/SELL): ")
        if not side or side not in ['BUY', 'SELL']: 
            print(f"{Fore.RED}Invalid side. Must be BUY or SELL{Style.RESET_ALL}")
            return
        
        # ...removed symbol info display...
            
        quantity = self._get_input("Quantity: ", float)
        if not quantity: return
        
        # Format quantity according to symbol requirements
        formatted_quantity = self._format_quantity(symbol, quantity)
        if formatted_quantity is None:
            print(f"{Fore.RED}Error formatting quantity{Style.RESET_ALL}")
            return
        
        # Validate parameters
        valid, message = self._validate_order_params(symbol, formatted_quantity)
        if not valid:
            print(f"{Fore.RED}Validation error: {message}{Style.RESET_ALL}")
            return
        
        if formatted_quantity != quantity:
            print(f"{Fore.YELLOW}Quantity adjusted to {formatted_quantity} to meet symbol requirements{Style.RESET_ALL}")
    
        try:
            order = self.bot.market_orders.place_order(symbol, side, formatted_quantity)
            self.bot.order_history.append(order)
            self._display_order_result(order)
        except Exception as e:
            print(f"{Fore.RED}Market order error: {e}{Style.RESET_ALL}")
    
    def _handle_limit_order(self):
        symbol = self._get_input("Symbol: ")
        if not symbol: return
        
        side = self._get_input("Side (BUY/SELL): ")
        if not side or side not in ['BUY', 'SELL']: 
            print(f"{Fore.RED}Invalid side. Must be BUY or SELL{Style.RESET_ALL}")
            return
        
        # ...removed symbol info display...
            
        quantity = self._get_input("Quantity: ", float)
        if not quantity: return
        
        # Format quantity according to symbol requirements
        formatted_quantity = self._format_quantity(symbol, quantity)
        if formatted_quantity is None:
            print(f"{Fore.RED}Error formatting quantity{Style.RESET_ALL}")
            return
        
        if formatted_quantity != quantity:
            print(f"{Fore.YELLOW}Quantity adjusted to {formatted_quantity} to meet symbol requirements{Style.RESET_ALL}")
        
        # Display current price before asking for limit price
        try:
            current_price = self.bot.get_current_price(symbol)
            formatted_current_price = self._format_price(symbol, current_price)
            print(f"{Fore.YELLOW}Current {symbol} price: {formatted_current_price}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error getting current price: {e}{Style.RESET_ALL}")
            return
            
        price = self._get_input("Limit Price: ", float)
        if not price: return
        
        # Format price according to symbol requirements
        formatted_price = self._format_price(symbol, price)
        if formatted_price is None:
            print(f"{Fore.RED}Error formatting price{Style.RESET_ALL}")
            return
        
        # Validate parameters
        valid, message = self._validate_order_params(symbol, formatted_quantity, formatted_price)
        if not valid:
            print(f"{Fore.RED}Validation error: {message}{Style.RESET_ALL}")
            return
        
        if formatted_price != price:
            print(f"{Fore.YELLOW}Price adjusted to {formatted_price} to meet symbol requirements{Style.RESET_ALL}")
    
        try:
            order = self.bot.limit_orders.place_order(symbol, side, formatted_quantity, formatted_price)
            self.bot.order_history.append(order)
            self._display_order_result(order)
        except Exception as e:
            print(f"{Fore.RED}Limit order error: {e}{Style.RESET_ALL}")
    
    def _handle_oco_order(self):
        symbol = self._get_input("Symbol: ")
        if not symbol: return
        
        side = self._get_input("Side (BUY/SELL): ")
        if not side or side not in ['BUY', 'SELL']: 
            print(f"{Fore.RED}Invalid side. Must be BUY or SELL{Style.RESET_ALL}")
            return
        
        # ...removed symbol info display...
        
        quantity = self._get_input("Quantity: ", float)
        if not quantity: return
        
        # Format quantity according to symbol requirements
        formatted_quantity = self._format_quantity(symbol, quantity)
        if formatted_quantity is None:
            print(f"{Fore.RED}Error formatting quantity{Style.RESET_ALL}")
            return
            
        if formatted_quantity != quantity:
            print(f"{Fore.YELLOW}Quantity adjusted to {formatted_quantity} to meet symbol requirements{Style.RESET_ALL}")
        
        # Display current price for reference
        try:
            current_price = self.bot.get_current_price(symbol)
            formatted_current_price = self._format_price(symbol, current_price)
            print(f"{Fore.YELLOW}Current {symbol} price: {formatted_current_price}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error getting current price: {e}{Style.RESET_ALL}")
            return
        
        limit_price = self._get_input("Limit price: ", float)
        if not limit_price: return
        
        stop_price = self._get_input("Stop price: ", float)
        if not stop_price: return
        
        stop_limit_price = self._get_input("Stop limit price: ", float)
        if not stop_limit_price: return
        
        # Format all prices according to symbol requirements
        formatted_limit_price = self._format_price(symbol, limit_price)
        formatted_stop_price = self._format_price(symbol, stop_price)
        formatted_stop_limit_price = self._format_price(symbol, stop_limit_price)
        
        if any(p is None for p in [formatted_limit_price, formatted_stop_price, formatted_stop_limit_price]):
            print(f"{Fore.RED}Error formatting prices{Style.RESET_ALL}")
            return
        
        # Validate all parameters
        for price_name, price_val in [("limit", formatted_limit_price), ("stop", formatted_stop_price), ("stop_limit", formatted_stop_limit_price)]:
            valid, message = self._validate_order_params(symbol, formatted_quantity, price_val)
            if not valid:
                print(f"{Fore.RED}Validation error for {price_name} price: {message}{Style.RESET_ALL}")
                return
        
        # Show adjustments if any
        if formatted_limit_price != limit_price:
            print(f"{Fore.YELLOW}Limit price adjusted to {formatted_limit_price}{Style.RESET_ALL}")
        if formatted_stop_price != stop_price:
            print(f"{Fore.YELLOW}Stop price adjusted to {formatted_stop_price}{Style.RESET_ALL}")
        if formatted_stop_limit_price != stop_limit_price:
            print(f"{Fore.YELLOW}Stop limit price adjusted to {formatted_stop_limit_price}{Style.RESET_ALL}")
        
        # Validate OCO price logic
        if side == 'SELL':
            if formatted_limit_price <= formatted_stop_price:
                print(f"{Fore.RED}For SELL orders: Limit price must be > Stop price{Style.RESET_ALL}")
                return
        else:  # BUY
            if formatted_limit_price >= formatted_stop_price:
                print(f"{Fore.RED}For BUY orders: Limit price must be < Stop price{Style.RESET_ALL}")
                return
        
        try:
            oco_id = self.bot.oco_orders.place_oco_order(
                symbol, side, formatted_quantity, formatted_limit_price, 
                formatted_stop_price, formatted_stop_limit_price
            )
            print(f"{Fore.GREEN}OCO order placed successfully: {oco_id}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}OCO order error: {e}{Style.RESET_ALL}")
    
    def _handle_twap_order(self):
        symbol = self._get_input("Symbol: ")
        if not symbol: return
        
        side = self._get_input("Side (BUY/SELL): ")
        if not side or side not in ['BUY', 'SELL']: 
            print(f"{Fore.RED}Invalid side. Must be BUY or SELL{Style.RESET_ALL}")
            return
        
        # ...removed symbol info display...
        
        total_quantity = self._get_input("Total quantity: ", float)
        if not total_quantity: return
        
        # Format quantity
        formatted_total_quantity = self._format_quantity(symbol, total_quantity)
        if formatted_total_quantity is None:
            print(f"{Fore.RED}Error formatting quantity{Style.RESET_ALL}")
            return
            
        if formatted_total_quantity != total_quantity:
            print(f"{Fore.YELLOW}Total quantity adjusted to {formatted_total_quantity}{Style.RESET_ALL}")
        
        duration = self._get_input("Duration (minutes): ", int)
        if not duration or duration <= 0: 
            print(f"{Fore.RED}Duration must be positive{Style.RESET_ALL}")
            return
        
        # Validate parameters
        valid, message = self._validate_order_params(symbol, formatted_total_quantity)
        if not valid:
            print(f"{Fore.RED}Validation error: {message}{Style.RESET_ALL}")
            return
        
        try:
            job_id = self.bot.twap_orders.start_twap_order(symbol, side, formatted_total_quantity, duration)
            print(f"{Fore.GREEN}TWAP order started successfully: {job_id}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}TWAP order error: {e}{Style.RESET_ALL}")
    
    def _handle_grid_strategy(self):
        symbol = self._get_input("Symbol: ")
        if not symbol: return
        
        # ...removed symbol info display...
        
        try:
            current_price = self.bot.get_current_price(symbol)
            formatted_current_price = self._format_price(symbol, current_price)
            print(f"{Fore.YELLOW}Current {symbol} price: {formatted_current_price}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error getting current price: {e}{Style.RESET_ALL}")
            return
        
        lower_price = self._get_input("Lower price: ", float)
        if not lower_price: return
        
        upper_price = self._get_input("Upper price: ", float)
        if not upper_price: return
        
        if lower_price >= upper_price:
            print(f"{Fore.RED}Lower price must be less than upper price{Style.RESET_ALL}")
            return
        
        grid_count = self._get_input("Grid levels: ", int)
        if not grid_count or grid_count < 2: 
            print(f"{Fore.RED}Grid levels must be at least 2{Style.RESET_ALL}")
            return
        
        total_quantity = self._get_input("Total quantity: ", float)
        if not total_quantity: return
        
        # Format prices and quantity
        formatted_lower_price = self._format_price(symbol, lower_price)
        formatted_upper_price = self._format_price(symbol, upper_price)
        formatted_total_quantity = self._format_quantity(symbol, total_quantity)
        
        if any(v is None for v in [formatted_lower_price, formatted_upper_price, formatted_total_quantity]):
            print(f"{Fore.RED}Error formatting parameters{Style.RESET_ALL}")
            return
        
        # Show adjustments
        if formatted_lower_price != lower_price:
            print(f"{Fore.YELLOW}Lower price adjusted to {formatted_lower_price}{Style.RESET_ALL}")
        if formatted_upper_price != upper_price:
            print(f"{Fore.YELLOW}Upper price adjusted to {formatted_upper_price}{Style.RESET_ALL}")
        if formatted_total_quantity != total_quantity:
            print(f"{Fore.YELLOW}Total quantity adjusted to {formatted_total_quantity}{Style.RESET_ALL}")
        
        try:
            grid_id = self.bot.grid_orders.create_grid_strategy(
                symbol, formatted_lower_price, formatted_upper_price, grid_count, formatted_total_quantity
            )
            self.bot.grid_orders.start_grid_strategy(grid_id)
            print(f"{Fore.GREEN}Grid strategy started successfully: {grid_id}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Grid strategy error: {e}{Style.RESET_ALL}")
    
    def _handle_balance(self):
        try:
            balances = self.bot.get_balance()
            print(f"\n{Fore.BLUE}ACCOUNT BALANCES{Style.RESET_ALL}")
            
            # Filter out zero balances and prepare data for tabulate
            data = []
            for asset, amounts in balances.items():
                available = float(amounts.get('available', 0))
                wallet = float(amounts.get('wallet', 0))
                
                # Only show assets with non-zero balances
                if available > 0 or wallet > 0:
                    data.append([
                        asset,
                        f"{available:.8f}",
                        f"{wallet:.8f}"
                    ])
            
            if data:
                headers = ['Asset', 'Available', 'Wallet Balance']
                print(tabulate(data, headers=headers, tablefmt='grid'))
            else:
                print(f"{Fore.YELLOW}No balances to display{Style.RESET_ALL}")
            
        except Exception as e:
            print(f"{Fore.RED}Balance error: {e}{Style.RESET_ALL}")
    
    def _handle_price(self):
        symbol = self._get_input("Symbol: ")
        if not symbol: return
        
        duration = self._get_input("Duration in seconds (0 for continuous): ", int)
        if duration is None: return
        
        if duration < 0:
            print(f"{Fore.RED}Duration cannot be negative{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.YELLOW}Press Ctrl+C to stop monitoring{Style.RESET_ALL}")
        
        def price_callback(symbol, price, timestamp):
            formatted_price = self._format_price(symbol, price)
            print(f"\r{Fore.BLUE}{timestamp} | {symbol}: {formatted_price}{Style.RESET_ALL}", end='')
        
        try:
            self.bot.monitor_price(symbol, duration, price_callback)
            print()  # New line after monitoring ends
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Price monitoring stopped{Style.RESET_ALL}")
        except Exception as e:
            print(f"\n{Fore.RED}Price monitoring error: {e}{Style.RESET_ALL}")
    
    def _handle_order_history(self):
        try:
            # Get filter parameters
            symbol = self._get_input("Symbol (or press Enter for all): ")
            limit = self._get_input("Number of orders to show (default 10): ", int)
            if not limit:
                limit = 10

            # Fetch order history from API
            orders = self.bot.get_order_history(symbol=symbol if symbol else None, limit=limit)

            if not orders:
                print(f"{Fore.YELLOW}No orders found in history{Style.RESET_ALL}")
                return

            data = []
            for order in orders:
                display_price = f"{order.price:.4f}" if getattr(order, 'price', None) else "Market"
                data.append([
                    str(order.order_id)[:8] + "..." if len(str(order.order_id)) > 8 else str(order.order_id),
                    order.symbol,
                    order.side,
                    f"{order.quantity:.6f}",
                    display_price,
                    getattr(order, 'status', 'Unknown'),
                    order.timestamp.strftime('%Y-%m-%d %H:%M:%S') if hasattr(order, 'timestamp') else 'N/A',
                    getattr(order, 'order_type', 'Unknown')
                ])

            headers = ['Order ID', 'Symbol', 'Side', 'Quantity', 'Price', 'Status', 'Time', 'Type']
            print(f"\n{Fore.BLUE}ORDER HISTORY{Style.RESET_ALL}")
            print(tabulate(data, headers=headers, tablefmt='grid'))

            # Show summary if we have orders
            if data:
                buy_orders = [order for order in orders if order.side == 'BUY']
                sell_orders = [order for order in orders if order.side == 'SELL']

                print(f"\n{Fore.CYAN}Summary:{Style.RESET_ALL}")
                print(f"Total Orders: {len(orders)}")
                print(f"Buy Orders: {len(buy_orders)}")
                print(f"Sell Orders: {len(sell_orders)}")

                # Calculate total volume if prices are available
                total_volume = sum((getattr(o, 'quantity', 0) * getattr(o, 'price', 0)) for o in orders if hasattr(o, 'price') and getattr(o, 'price', None))
                if total_volume > 0:
                    print(f"Total Volume: {total_volume:.4f}")

        except Exception as e:
            print(f"{Fore.RED}Error fetching order history: {e}{Style.RESET_ALL}")
    
    def _handle_status(self):
        print(f"\n{Fore.BLUE}TRADING STATUS{Style.RESET_ALL}")
        
        try:
            # Recent orders with actual prices
            if self.bot.order_history:
                recent_orders = self.bot.order_history[-5:]
                print(f"\n{Fore.CYAN}Recent Orders:{Style.RESET_ALL}")
                for order in recent_orders:
                    price_str = f"{order.price:.4f}" if order.price else "Market"
                    total_value = f"{(order.quantity * order.price):.4f}" if order.price else "N/A"
                    print(f"  {order.symbol} {order.side} {order.quantity:.6f} @ {price_str} (Total: {total_value})")
            else:
                print(f"\n{Fore.YELLOW}No recent orders{Style.RESET_ALL}")
        
            # TWAP jobs
            try:
                twap_jobs = self.bot.twap_orders.get_twap_jobs()
                if twap_jobs:
                    print(f"\n{Fore.CYAN}TWAP Jobs: {len(twap_jobs)}{Style.RESET_ALL}")
                    for job_id, job in twap_jobs.items():
                        avg_price = 0
                        if job.get('orders'):
                            total_cost = sum(o.quantity * o.price for o in job['orders'] if hasattr(o, 'price') and o.price)
                            total_qty = sum(o.quantity for o in job['orders'] if hasattr(o, 'quantity'))
                            avg_price = total_cost / total_qty if total_qty > 0 else 0
                    
                        print(f"  {job_id}: {job.get('status', 'Unknown')} ({job.get('completed', 0)}/{job.get('parts', 0)}) Avg: {avg_price:.4f}")
            except Exception as e:
                print(f"{Fore.RED}Error getting TWAP status: {e}{Style.RESET_ALL}")
        
            # OCO orders
            try:
                oco_orders = self.bot.oco_orders.get_oco_orders()
                if oco_orders:
                    print(f"\n{Fore.CYAN}OCO Orders: {len(oco_orders)}{Style.RESET_ALL}")
                    for oco_id, oco in oco_orders.items():
                        print(f"  {oco_id}: {oco.get('status', 'Unknown')}")
            except Exception as e:
                print(f"{Fore.RED}Error getting OCO status: {e}{Style.RESET_ALL}")
        
            # Grid strategies  
            try:
                grid_strategies = self.bot.grid_orders.get_grid_strategies()
                if grid_strategies:
                    print(f"\n{Fore.CYAN}Grid Strategies: {len(grid_strategies)}{Style.RESET_ALL}")
                    for grid_id, grid in grid_strategies.items():
                        print(f"  {grid_id}: {grid.get('status', 'Unknown')} (Trades: {grid.get('total_trades', 0)}, P&L: {grid.get('profit_loss', 0):.4f})")
            except Exception as e:
                print(f"{Fore.RED}Error getting Grid status: {e}{Style.RESET_ALL}")
                
        except Exception as e:
            print(f"{Fore.RED}Error getting status: {e}{Style.RESET_ALL}")

    def _display_order_result(self, order):
        """Display order execution results"""
        try:
            formatted_quantity = self._format_quantity(order.symbol, order.quantity)
            formatted_price = self._format_price(order.symbol, order.price) if order.price else None
            formatted_total = self._format_price(order.symbol, order.quantity * order.price) if order.price else None
            
            order_data = [
                ['Order ID', str(order.order_id)],
                ['Symbol', order.symbol],
                ['Side', order.side],
                ['Quantity', f"{formatted_quantity}"],
                ['Price', f"{formatted_price}" if formatted_price else "Market"],
                ['Total', f"{formatted_total}" if formatted_total else "N/A"],
                ['Status', "FILLED" if order.price else "PENDING"],
                ['Type', getattr(order, 'order_type', 'Unknown')],
                ['Time', order.timestamp.strftime('%H:%M:%S') if hasattr(order, 'timestamp') else 'N/A']
            ]
            
            print(f"\n{Fore.GREEN}ORDER EXECUTED{Style.RESET_ALL}")
            print(tabulate(order_data, headers=['Field', 'Value'], tablefmt='grid'))
            
        except Exception as e:
            print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Order placed: {order.symbol} {order.side} {order.quantity}{Style.RESET_ALL}")
