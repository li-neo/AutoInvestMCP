"""
富途API接口实现
"""
import json
import os
import time
from typing import Dict, List, Any, Optional
import pandas as pd
from futu import OpenQuoteContext, OpenHKTradeContext, OpenUSTradeContext, TrdEnv
from futu import RET_OK, RET_ERROR, KL_FIELD, KLType, TrdSide, OrderType, TrdMarket, SecurityType

from src.data_api.base_api import BaseAPI
from config.constants import (
    TIMEFRAME_1M, TIMEFRAME_5M, TIMEFRAME_15M, TIMEFRAME_30M,
    TIMEFRAME_1H, TIMEFRAME_4H, TIMEFRAME_1D, TIMEFRAME_1W,
    MARKET_TYPE_A_SHARE, MARKET_TYPE_US, MARKET_TYPE_HK
)


class FutuAPI(BaseAPI):
    """富途API实现类"""
    
    # 时间周期映射
    TIMEFRAME_MAP = {
        TIMEFRAME_1M: KLType.K_1M,
        TIMEFRAME_5M: KLType.K_5M,
        TIMEFRAME_15M: KLType.K_15M,
        TIMEFRAME_30M: KLType.K_30M,
        TIMEFRAME_1H: KLType.K_60M,
        TIMEFRAME_4H: KLType.K_4H,
        TIMEFRAME_1D: KLType.K_DAY,
        TIMEFRAME_1W: KLType.K_WEEK,
    }
    
    # 市场类型映射
    MARKET_MAP = {
        MARKET_TYPE_A_SHARE: TrdMarket.CHINAA,
        MARKET_TYPE_US: TrdMarket.US,
        MARKET_TYPE_HK: TrdMarket.HK,
    }
    
    def __init__(self, host: str = None, port: int = None, 
                 api_key: str = None, api_secret: str = None, 
                 config_path: str = None,
                 market: str = MARKET_TYPE_HK):
        """初始化富途API接口
        
        Args:
            host: FutuOpenD主机地址
            port: FutuOpenD端口
            api_key: API密钥（如适用）
            api_secret: API密钥对应的secret（如适用）
            config_path: 配置文件路径，如果其他参数为None则从配置文件读取
            market: 默认交易市场
        """
        self.quote_ctx = None
        self.trade_ctx = None
        self.host = host
        self.port = port
        self.api_key = api_key
        self.api_secret = api_secret
        self.config_path = config_path
        self.market = market
        
        # 如果没有提供参数，尝试从配置文件读取
        if (not host or not port) and config_path:
            self._load_config(config_path)
    
    def _load_config(self, config_path: str):
        """从配置文件加载配置
        
        Args:
            config_path: 配置文件路径
        """
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                futu_config = config.get('api', {}).get('futu', {})
                self.host = futu_config.get('host', self.host)
                self.port = futu_config.get('port', self.port)
                self.api_key = futu_config.get('api_key', self.api_key)
                self.api_secret = futu_config.get('api_secret', self.api_secret)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"加载配置文件失败: {e}")
    
    def connect(self) -> bool:
        """连接到富途API
        
        Returns:
            bool: 连接是否成功
        """
        try:
            # 连接行情API
            self.quote_ctx = OpenQuoteContext(host=self.host, port=self.port)
            
            # 连接交易API
            if self.market == MARKET_TYPE_HK:
                self.trade_ctx = OpenHKTradeContext(host=self.host, port=self.port)
            elif self.market == MARKET_TYPE_US:
                self.trade_ctx = OpenUSTradeContext(host=self.host, port=self.port)
            else:
                # 不支持A股交易
                print(f"不支持市场{self.market}的交易API连接")
                self.trade_ctx = None
            
            return True
        except Exception as e:
            print(f"连接富途API失败: {e}")
            return False
    
    def _ensure_connection(self):
        """确保API已连接"""
        if not self.quote_ctx:
            self.connect()
    
    def get_market_data(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """获取市场行情数据
        
        Args:
            symbol: 股票代码，例如 'HK.00700'
            timeframe: 时间周期，例如 '1d'
            limit: 获取的K线数量
            
        Returns:
            pandas.DataFrame: 包含OHLCV的DataFrame
        """
        self._ensure_connection()
        
        # 检查并转换时间周期格式
        futu_timeframe = self.TIMEFRAME_MAP.get(timeframe)
        if not futu_timeframe:
            raise ValueError(f"不支持的时间周期: {timeframe}")
        
        try:
            # 获取K线数据
            ret, data = self.quote_ctx.get_kline_data(
                code=symbol,
                ktype=futu_timeframe,
                num=limit
            )
            
            if ret != RET_OK:
                print(f"获取市场数据失败: {data}")
                return pd.DataFrame()
            
            # 重命名列以匹配统一格式
            data.rename(columns={
                'code': 'symbol',
                'time_key': 'timestamp',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            }, inplace=True)
            
            # 转换数据类型
            data['timestamp'] = pd.to_datetime(data['timestamp'])
            for col in ['open', 'high', 'low', 'close', 'volume']:
                data[col] = data[col].astype(float)
            
            # 设置索引
            data.set_index('timestamp', inplace=True)
            
            # 返回OHLCV数据
            return data[['open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e:
            print(f"获取市场数据失败: {e}")
            return pd.DataFrame()
    
    def get_ticker_info(self, symbol: str) -> Dict[str, Any]:
        """获取股票的基本信息
        
        Args:
            symbol: 股票代码，例如 'HK.00700'
            
        Returns:
            Dict: 包含股票基本信息的字典
        """
        self._ensure_connection()
                
        try:
            # 获取实时行情
            ret, data = self.quote_ctx.get_stock_quote([symbol])
            if ret != RET_OK:
                print(f"获取股票信息失败: {data}")
                return {}
            
            # 获取第一条记录
            info = data.iloc[0]
            
            # 获取股票基本信息
            ret2, basic_info = self.quote_ctx.get_stock_basicinfo(
                market=symbol.split('.')[0],
                code=symbol,
                stock_type=SecurityType.STOCK
            )
            
            if ret2 != RET_OK:
                basic_info_dict = {}
            else:
                basic_info_dict = basic_info.iloc[0].to_dict()
            
            # 合并信息
            return {
                'symbol': symbol,
                'name': basic_info_dict.get('name', ''),
                'price': float(info['last_price']),
                'volume': float(info['volume']),
                'turnover': float(info['turnover']),
                'change_percent': float(info['change_rate']) * 100,
                'high': float(info['high']),
                'low': float(info['low']),
                'open': float(info['open']),
                'prev_close': float(info['prev_close']),
                'lot_size': basic_info_dict.get('lot_size', 0),
                'market_val': basic_info_dict.get('market_val', 0)
            }
        except Exception as e:
            print(f"获取股票信息失败: {e}")
            return {}
    
    def get_symbols(self, market: Optional[str] = None) -> List[str]:
        """获取可交易的所有股票代码
        
        Args:
            market: 可选，指定市场，如 'HK'、'US'
            
        Returns:
            List[str]: 股票代码列表
        """
        self._ensure_connection()
                
        try:
            if not market:
                market = self.market.split('股')[0] if '股' in self.market else self.market
                
            # 富途API的市场代码
            if market == MARKET_TYPE_HK or market == 'HK':
                market_code = 'HK'
            elif market == MARKET_TYPE_US or market == 'US':
                market_code = 'US'
            elif market == MARKET_TYPE_A_SHARE or market == 'A':
                market_code = 'SH,SZ'
            else:
                raise ValueError(f"不支持的市场: {market}")
            
            # 获取股票列表
            ret, data = self.quote_ctx.get_stock_basicinfo(
                market=market_code,
                stock_type=SecurityType.STOCK
            )
            
            if ret != RET_OK:
                print(f"获取股票列表失败: {data}")
                return []
                
            return data['code'].tolist()
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            return []
    
    def place_order(self, symbol: str, order_type: str, side: str, 
                    amount: float, price: Optional[float] = None) -> Dict[str, Any]:
        """下单交易
        
        Args:
            symbol: 股票代码，例如 'HK.00700'
            order_type: 订单类型，如'LIMIT'、'MARKET'等
            side: 交易方向，'BUY'或'SELL'
            amount: 交易数量
            price: 交易价格，对于市价单可为None
            
        Returns:
            Dict: 订单信息
        """
        self._ensure_connection()
        
        if not self.trade_ctx:
            print("交易API未连接或不支持此市场")
            return {}
        
        try:
            # 转换订单类型
            if order_type.upper() == 'MARKET':
                futu_order_type = OrderType.MARKET
            elif order_type.upper() == 'LIMIT':
                futu_order_type = OrderType.NORMAL
                if not price:
                    raise ValueError("限价单需要提供价格")
            else:
                raise ValueError(f"不支持的订单类型: {order_type}")
            
            # 转换交易方向
            if side.upper() == 'BUY':
                futu_side = TrdSide.BUY
            elif side.upper() == 'SELL':
                futu_side = TrdSide.SELL
            else:
                raise ValueError(f"不支持的交易方向: {side}")
            
            # 下单
            ret, data = self.trade_ctx.place_order(
                price=price if price else 0,
                qty=amount,
                code=symbol,
                trd_side=futu_side,
                order_type=futu_order_type,
                trd_env=TrdEnv.REAL  # 真实环境
            )
            
            if ret != RET_OK:
                print(f"下单失败: {data}")
                return {}
            
            # 获取订单ID
            order_id = data['order_id'][0]
            
            # 获取订单详情
            return self.get_order_status(order_id)
            
        except Exception as e:
            print(f"下单失败: {e}")
            return {}
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """查询订单状态
        
        Args:
            order_id: 订单ID
            
        Returns:
            Dict: 订单状态信息
        """
        self._ensure_connection()
        
        if not self.trade_ctx:
            print("交易API未连接或不支持此市场")
            return {}
                
        try:
            # 查询订单
            ret, data = self.trade_ctx.order_list_query(
                order_id=order_id
            )
            
            if ret != RET_OK or len(data) == 0:
                print(f"获取订单状态失败: {data}")
                return {}
            
            # 获取第一条记录
            order = data.iloc[0]
            
            return {
                'order_id': order['order_id'],
                'symbol': order['code'],
                'side': 'BUY' if order['trd_side'] == TrdSide.BUY else 'SELL',
                'type': 'LIMIT' if order['order_type'] == OrderType.NORMAL else 'MARKET',
                'status': order['order_status'],
                'price': float(order['price']),
                'qty': float(order['qty']),
                'dealt_qty': float(order['dealt_qty']),
                'dealt_amount': float(order['dealt_amount']),
                'create_time': order['create_time'],
                'updated_time': order['updated_time']
            }
        except Exception as e:
            print(f"获取订单状态失败: {e}")
            return {}
    
    def cancel_order(self, order_id: str) -> bool:
        """取消订单
        
        Args:
            order_id: 订单ID
            
        Returns:
            bool: 取消是否成功
        """
        self._ensure_connection()
        
        if not self.trade_ctx:
            print("交易API未连接或不支持此市场")
            return False
                
        try:
            ret, data = self.trade_ctx.modify_order(
                modify_order_op=1,  # 取消订单
                order_id=order_id,
                price=0,
                qty=0
            )
            
            return ret == RET_OK
        except Exception as e:
            print(f"取消订单失败: {e}")
            return False
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息
        
        Returns:
            Dict: 账户信息，包括余额等
        """
        self._ensure_connection()
        
        if not self.trade_ctx:
            print("交易API未连接或不支持此市场")
            return {}
                
        try:
            # 获取账户资金
            ret, data = self.trade_ctx.accinfo_query()
            
            if ret != RET_OK:
                print(f"获取账户信息失败: {data}")
                return {}
            
            # 获取第一条记录
            account = data.iloc[0]
            
            # 获取持仓
            ret2, positions = self.trade_ctx.position_list_query()
            position_list = []
            
            if ret2 == RET_OK:
                for _, pos in positions.iterrows():
                    position_list.append({
                        'symbol': pos['code'],
                        'qty': float(pos['qty']),
                        'cost_price': float(pos['cost_price']),
                        'market_value': float(pos['market_val']),
                        'profit': float(pos['pl_val']),
                        'profit_percent': float(pos['pl_ratio']) * 100
                    })
            
            return {
                'cash': float(account['cash']),
                'total_assets': float(account['total_assets']),
                'market_value': float(account['market_val']),
                'buying_power': float(account['buying_power']),
                'positions': position_list
            }
        except Exception as e:
            print(f"获取账户信息失败: {e}")
            return {}