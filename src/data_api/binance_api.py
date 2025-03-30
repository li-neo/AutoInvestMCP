"""
币安API接口实现
"""
import json
import os
import time
from typing import Dict, List, Any, Optional
import pandas as pd
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
from dotenv import load_dotenv

from src.data_api.base_api import BaseAPI
from config.constants import (
    TIMEFRAME_1M, TIMEFRAME_5M, TIMEFRAME_15M, TIMEFRAME_30M,
    TIMEFRAME_1H, TIMEFRAME_4H, TIMEFRAME_1D, TIMEFRAME_1W
)

# 加载环境变量
load_dotenv()

class BinanceAPI(BaseAPI):
    """币安API实现类"""
    
    # 时间周期映射
    TIMEFRAME_MAP = {
        TIMEFRAME_1M: Client.KLINE_INTERVAL_1MINUTE,
        TIMEFRAME_5M: Client.KLINE_INTERVAL_5MINUTE,
        TIMEFRAME_15M: Client.KLINE_INTERVAL_15MINUTE,
        TIMEFRAME_30M: Client.KLINE_INTERVAL_30MINUTE,
        TIMEFRAME_1H: Client.KLINE_INTERVAL_1HOUR,
        TIMEFRAME_4H: Client.KLINE_INTERVAL_4HOUR,
        TIMEFRAME_1D: Client.KLINE_INTERVAL_1DAY,
        TIMEFRAME_1W: Client.KLINE_INTERVAL_1WEEK,
    }
    
    def __init__(self, api_key: str = None, api_secret: str = None, config_path: str = None):
        """初始化币安API接口
        
        Args:
            api_key: API密钥
            api_secret: API密钥对应的secret
            config_path: 配置文件路径，如果api_key和api_secret为None则从配置文件读取
        """
        self.client = None
        self.api_key = api_key
        self.api_secret = api_secret
        self.config_path = config_path
        
        # 首先尝试从环境变量读取API密钥
        if not self.api_key:
            self.api_key = os.environ.get('BINANCE_API_KEY')
        
        if not self.api_secret:
            self.api_secret = os.environ.get('BINANCE_API_SECRET')
        
        # 如果环境变量中没有，尝试从配置文件读取
        if (not self.api_key or not self.api_secret) and config_path:
            self._load_config(config_path)
    
    def _load_config(self, config_path: str):
        """从配置文件加载API密钥
        
        Args:
            config_path: 配置文件路径
        """
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                # 只有在环境变量中未设置的情况下，才从配置文件加载
                if not self.api_key:
                    self.api_key = config.get('api', {}).get('binance', {}).get('api_key')
                if not self.api_secret:
                    self.api_secret = config.get('api', {}).get('binance', {}).get('api_secret')
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"加载配置文件失败: {e}")
    
    def connect(self) -> bool:
        """连接到币安API
        
        Returns:
            bool: 连接是否成功
        """
        try:
            self.client = Client(self.api_key, self.api_secret)
            # 测试API连接
            self.client.get_system_status()
            return True
        except (BinanceAPIException, BinanceRequestException) as e:
            print(f"连接币安API失败: {e}")
            return False
    
    def get_market_data(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """获取市场行情数据
        
        Args:
            symbol: 交易对，例如 'BTCUSDT'
            timeframe: 时间周期，例如 '1d'
            limit: 获取的K线数量
            
        Returns:
            pandas.DataFrame: 包含OHLCV的DataFrame
        """
        if not self.client:
            if not self.connect():
                return pd.DataFrame()
        
        # 检查并转换时间周期格式
        binance_timeframe = self.TIMEFRAME_MAP.get(timeframe)
        if not binance_timeframe:
            raise ValueError(f"不支持的时间周期: {timeframe}")
        
        try:
            # 获取K线数据
            klines = self.client.get_klines(
                symbol=symbol,
                interval=binance_timeframe,
                limit=limit
            )
            
            # 转换为DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # 转换数据类型
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            # 设置索引
            df.set_index('timestamp', inplace=True)
            
            # 返回OHLCV数据
            return df[['open', 'high', 'low', 'close', 'volume']]
        
        except BinanceAPIException as e:
            print(f"获取市场数据失败: {e}")
            return pd.DataFrame()
    
    def get_ticker_info(self, symbol: str) -> Dict[str, Any]:
        """获取交易对的基本信息
        
        Args:
            symbol: 交易对，例如 'BTCUSDT'
            
        Returns:
            Dict: 包含交易对基本信息的字典
        """
        if not self.client:
            if not self.connect():
                return {}
                
        try:
            ticker = self.client.get_ticker(symbol=symbol)
            return {
                'symbol': ticker['symbol'],
                'price': float(ticker['lastPrice']),
                'volume': float(ticker['volume']),
                'change_percent': float(ticker['priceChangePercent']),
                'high_24h': float(ticker['highPrice']),
                'low_24h': float(ticker['lowPrice']),
            }
        except BinanceAPIException as e:
            print(f"获取交易对信息失败: {e}")
            return {}
    
    def get_symbols(self, market: Optional[str] = None) -> List[str]:
        """获取可交易的所有交易对
        
        Args:
            market: 可选，指定市场，如 'USDT'
            
        Returns:
            List[str]: 交易对代码列表
        """
        if not self.client:
            if not self.connect():
                return []
                
        try:
            exchange_info = self.client.get_exchange_info()
            symbols = [s['symbol'] for s in exchange_info['symbols'] if s['status'] == 'TRADING']
            
            # 如果指定了市场，过滤交易对
            if market:
                symbols = [s for s in symbols if s.endswith(market)]
                
            return symbols
        except BinanceAPIException as e:
            print(f"获取交易对列表失败: {e}")
            return []
    
    def place_order(self, symbol: str, order_type: str, side: str, 
                    amount: float, price: Optional[float] = None) -> Dict[str, Any]:
        """下单交易
        
        Args:
            symbol: 交易对，例如 'BTCUSDT'
            order_type: 订单类型，如'LIMIT'、'MARKET'等
            side: 交易方向，'BUY'或'SELL'
            amount: 交易数量
            price: 交易价格，对于市价单可为None
            
        Returns:
            Dict: 订单信息
        """
        if not self.client:
            if not self.connect():
                return {}
        
        try:
            # 统一订单类型为币安API需要的格式
            binance_order_type = order_type.upper()
            binance_side = side.upper()
            
            params = {
                'symbol': symbol,
                'side': binance_side,
                'type': binance_order_type,
                'quantity': amount,
            }
            
            # 如果是限价单，需要提供价格
            if binance_order_type == 'LIMIT':
                if not price:
                    raise ValueError("限价单需要提供价格")
                params['price'] = price
                params['timeInForce'] = 'GTC'  # Good Till Cancelled
            
            # 下单
            order = self.client.create_order(**params)
            
            # 格式化返回数据
            return {
                'order_id': order['orderId'],
                'symbol': order['symbol'],
                'side': order['side'],
                'type': order['type'],
                'status': order['status'],
                'created_time': order['transactTime'],
            }
            
        except BinanceAPIException as e:
            print(f"下单失败: {e}")
            return {}
    
    def get_order_status(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """查询订单状态
        
        Args:
            order_id: 订单ID
            symbol: 交易对，币安API需要提供symbol来查询订单
            
        Returns:
            Dict: 订单状态信息
        """
        if not self.client:
            if not self.connect():
                return {}
                
        try:
            order = self.client.get_order(symbol=symbol, orderId=order_id)
            return {
                'order_id': order['orderId'],
                'symbol': order['symbol'],
                'side': order['side'],
                'type': order['type'],
                'status': order['status'],
                'price': float(order['price']) if order['price'] != '0.00000000' else None,
                'executed_qty': float(order['executedQty']),
                'cummulative_quote_qty': float(order['cummulativeQuoteQty']),
            }
        except BinanceAPIException as e:
            print(f"获取订单状态失败: {e}")
            return {}
    
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """取消订单
        
        Args:
            order_id: 订单ID
            symbol: 交易对，币安API需要提供symbol来取消订单
            
        Returns:
            bool: 取消是否成功
        """
        if not self.client:
            if not self.connect():
                return False
                
        try:
            result = self.client.cancel_order(symbol=symbol, orderId=order_id)
            return result['status'] == 'CANCELED'
        except BinanceAPIException as e:
            print(f"取消订单失败: {e}")
            return False
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息
        
        Returns:
            Dict: 账户信息，包括余额等
        """
        if not self.client:
            if not self.connect():
                return {}
                
        try:
            account = self.client.get_account()
            
            # 筛选有余额的资产
            balances = [{
                'asset': b['asset'],
                'free': float(b['free']),
                'locked': float(b['locked']),
                'total': float(b['free']) + float(b['locked'])
            } for b in account['balances'] if float(b['free']) > 0 or float(b['locked']) > 0]
            
            return {
                'account_type': account['accountType'],
                'can_trade': account['canTrade'],
                'can_withdraw': account['canWithdraw'],
                'balances': balances
            }
        except BinanceAPIException as e:
            print(f"获取账户信息失败: {e}")
            return {}