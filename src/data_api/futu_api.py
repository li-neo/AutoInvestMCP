"""
富途API接口，用于获取港股、美股和A股数据
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

from src.data_api.base_api import BaseDataAPI
from config.constants import (
    MARKET_TYPE_A_SHARE, MARKET_TYPE_US, MARKET_TYPE_HK,
    ORDER_TYPE_MARKET, ORDER_TYPE_LIMIT,
    ORDER_SIDE_BUY, ORDER_SIDE_SELL
)

# 尝试导入富途API，如果失败则使用模拟模式
try:
    import futu as ft
    FUTU_AVAILABLE = True
except ImportError:
    logging.warning("未安装富途API(futu-api)，将使用模拟模式")
    FUTU_AVAILABLE = False
    
    # 创建模拟的富途API类，用于测试
    class MockFutuAPI:
        """模拟的富途API类"""
        
        class KLType:
            K_1M = "1m"
            K_5M = "5m"
            K_15M = "15m"
            K_30M = "30m"
            K_60M = "60m"
            K_DAY = "1d"
            K_WEEK = "1w"
            K_MONTH = "1M"
        
        class TrdEnv:
            SIMULATE = 0
            REAL = 1
        
        class TrdSide:
            BUY = 0
            SELL = 1
        
        class TrdMarket:
            HK = "HK"
            US = "US"
            CN = "CN"
            
        class OrderType:
            NORMAL = 0
            MARKET = 1
            
        class RET_OK:
            """模拟的成功返回"""
            @staticmethod
            def check_err():
                return True

    class MockOpenQuoteContext:
        """模拟的行情上下文"""
        
        def __init__(self, host=None, port=None):
            self.host = host
            self.port = port
            self.connected = True
            
        def close(self):
            self.connected = False
            
        def get_market_snapshot(self, code_list):
            """获取市场快照"""
            data = {
                'code': code_list,
                'name': [f"模拟股票{code}" for code in code_list],
                'last_price': [np.random.uniform(10, 1000) for _ in code_list],
                'open_price': [np.random.uniform(10, 1000) for _ in code_list],
                'high_price': [np.random.uniform(10, 1000) for _ in code_list],
                'low_price': [np.random.uniform(10, 1000) for _ in code_list],
                'volume': [np.random.randint(1000, 10000000) for _ in code_list],
                'turnover': [np.random.randint(1000000, 1000000000) for _ in code_list],
                'pe_ratio': [np.random.uniform(5, 50) for _ in code_list],
                'lot_size': [100 for _ in code_list]
            }
            
            df = pd.DataFrame(data)
            return MockFutuAPI.RET_OK, df
            
        def request_history_kline(self, code, start=None, end=None, ktype=None, max_count=1000):
            """获取历史K线数据"""
            # 生成模拟的K线数据
            now = datetime.now()
            dates = [now - timedelta(days=i) for i in range(max_count)]
            dates.reverse()
            
            # 生成随机价格
            last_price = np.random.uniform(50, 200)
            prices = []
            volumes = []
            
            for i in range(max_count):
                change = np.random.normal(0, 1)
                last_price = max(last_price + change, 1)  # 确保价格为正
                prices.append(last_price)
                volumes.append(np.random.randint(1000, 10000000))
            
            data = {
                'code': [code] * max_count,
                'time_key': dates,
                'open': prices,
                'high': [p + np.random.uniform(0, 2) for p in prices],
                'low': [p - np.random.uniform(0, 2) for p in prices],
                'close': prices,
                'volume': volumes,
                'turnover': [v * p for v, p in zip(volumes, prices)]
            }
            
            df = pd.DataFrame(data)
            # 返回3个值以模拟真实API
            return MockFutuAPI.RET_OK, df, False

    class MockTradingContext:
        """模拟的交易上下文"""
        
        def __init__(self, host=None, port=None, trd_env=None, acc_id=None):
            self.host = host
            self.port = port
            self.trd_env = trd_env
            self.acc_id = acc_id
            self.connected = True
            
        def close(self):
            self.connected = False
            
        def place_order(self, code, qty, trd_side, order_type=None, price=None, trd_mkt=None):
            """下单"""
            data = {
                'code': [code],
                'order_id': [f"mock-order-{np.random.randint(10000, 99999)}"],
                'qty': [qty],
                'price': [price if price is not None else 0],
                'trd_side': [trd_side],
                'order_status': ['已提交']
            }
            
            df = pd.DataFrame(data)
            return MockFutuAPI.RET_OK, df
            
        def modify_order(self, order_id, qty=None, price=None):
            """修改订单"""
            data = {
                'order_id': [order_id],
                'qty': [qty if qty is not None else 0],
                'price': [price if price is not None else 0],
                'order_status': ['已修改']
            }
            
            df = pd.DataFrame(data)
            return MockFutuAPI.RET_OK, df
            
        def cancel_order(self, order_id):
            """取消订单"""
            data = {
                'order_id': [order_id],
                'order_status': ['已取消']
            }
            
            df = pd.DataFrame(data)
            return MockFutuAPI.RET_OK, df
            
        def get_order_list(self, status_filter_list=None):
            """获取订单列表"""
            data = {
                'code': ['HK.00700', 'US.AAPL', 'SH.600519'],
                'order_id': [f"mock-order-{i}" for i in range(3)],
                'qty': [100, 50, 200],
                'price': [500, 150, 1800],
                'trd_side': [0, 0, 1],  # 0-买入, 1-卖出
                'order_status': ['已成交', '已提交', '已成交']
            }
            
            df = pd.DataFrame(data)
            return MockFutuAPI.RET_OK, df
            
        def get_position_list(self):
            """获取持仓列表"""
            data = {
                'code': ['HK.00700', 'US.AAPL', 'SH.600519'],
                'qty': [200, 100, 50],
                'cost_price': [450, 130, 1700],
                'current_price': [500, 150, 1800],
                'market_value': [100000, 15000, 90000]
            }
            
            df = pd.DataFrame(data)
            return MockFutuAPI.RET_OK, df
            
        def get_account_info(self):
            """获取账户信息"""
            data = {
                'power': [100000],  # 购买力
                'total_assets': [500000],  # 总资产
                'cash': [200000],  # 现金
                'market_value': [300000]  # 持仓市值
            }
            
            df = pd.DataFrame(data)
            return MockFutuAPI.RET_OK, df
    
    # 替换富途API的主要类
    ft = MockFutuAPI()
    ft.OpenQuoteContext = MockOpenQuoteContext
    ft.OpenHKTradeContext = MockTradingContext
    ft.OpenUSTradeContext = MockTradingContext
    ft.OpenCNTradeContext = MockTradingContext


class FutuAPI(BaseDataAPI):
    """富途API封装"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化富途API
        
        Args:
            config: 配置信息，包含host, port, trd_env, acc_id等
        """
        super().__init__()
        
        self.config = config
        self.host = config.get('host', '127.0.0.1')
        self.port = config.get('port', 11111)
        self.trd_env = config.get('trd_env', ft.TrdEnv.SIMULATE)  # 默认使用模拟环境
        self.acc_id = config.get('acc_id')
        
        # 初始化行情和交易API
        self.quote_ctx = None
        self.trade_ctx_hk = None
        self.trade_ctx_us = None
        self.trade_ctx_cn = None
        
        # 市场与交易上下文的映射
        self.market_trade_ctx = {
            MARKET_TYPE_HK: lambda: self._get_hk_trade_ctx(),
            MARKET_TYPE_US: lambda: self._get_us_trade_ctx(),
            MARKET_TYPE_A_SHARE: lambda: self._get_cn_trade_ctx()
        }
        
    def _get_quote_ctx(self):
        """获取行情上下文"""
        if self.quote_ctx is None:
            self.quote_ctx = ft.OpenQuoteContext(host=self.host, port=self.port)
        return self.quote_ctx
    
    def _get_hk_trade_ctx(self):
        """获取港股交易上下文"""
        if self.trade_ctx_hk is None:
            self.trade_ctx_hk = ft.OpenHKTradeContext(host=self.host, port=self.port, trd_env=self.trd_env, acc_id=self.acc_id)
        return self.trade_ctx_hk
    
    def _get_us_trade_ctx(self):
        """获取美股交易上下文"""
        if self.trade_ctx_us is None:
            self.trade_ctx_us = ft.OpenUSTradeContext(host=self.host, port=self.port, trd_env=self.trd_env, acc_id=self.acc_id)
        return self.trade_ctx_us
    
    def _get_cn_trade_ctx(self):
        """获取A股交易上下文"""
        if self.trade_ctx_cn is None:
            self.trade_ctx_cn = ft.OpenCNTradeContext(host=self.host, port=self.port, trd_env=self.trd_env, acc_id=self.acc_id)
        return self.trade_ctx_cn
    
    def _convert_ktype(self, timeframe: str) -> str:
        """转换时间周期格式
        
        Args:
            timeframe: API中的时间周期格式
            
        Returns:
            str: 富途API中的K线类型
        """
        ktype_map = {
            '1m': ft.KLType.K_1M,
            '5m': ft.KLType.K_5M,
            '15m': ft.KLType.K_15M,
            '30m': ft.KLType.K_30M,
            '1h': ft.KLType.K_60M,
            '1d': ft.KLType.K_DAY,
            '1w': ft.KLType.K_WEEK,
            '1M': ft.KLType.K_MON  # 修改这里，使用正确的月线枚举值
        }
        return ktype_map.get(timeframe, ft.KLType.K_DAY)
    
    def _convert_order_type(self, order_type: str) -> int:
        """转换订单类型
        
        Args:
            order_type: API中的订单类型
            
        Returns:
            int: 富途API中的订单类型
        """
        if order_type == ORDER_TYPE_MARKET:
            return ft.OrderType.MARKET
        else:
            return ft.OrderType.NORMAL
    
    def _convert_order_side(self, side: str) -> int:
        """转换交易方向
        
        Args:
            side: API中的交易方向
            
        Returns:
            int: 富途API中的交易方向
        """
        if side == ORDER_SIDE_BUY:
            return ft.TrdSide.BUY
        else:
            return ft.TrdSide.SELL
    
    def _get_market_from_symbol(self, symbol: str) -> str:
        """从代码中识别市场类型
        
        Args:
            symbol: 股票代码
            
        Returns:
            str: 市场类型
        """
        # 移除可能存在的前缀
        clean_symbol = symbol.split('.')[-1].strip()
        
        if symbol.startswith(('HK.', 'hk.')):
            return MARKET_TYPE_HK
        elif symbol.startswith(('US.', 'us.')):
            return MARKET_TYPE_US
        elif symbol.startswith(('SH.', 'sh.', 'SZ.', 'sz.')):
            return MARKET_TYPE_A_SHARE
        # 尝试根据代码格式猜测市场
        elif clean_symbol.isdigit():
            if len(clean_symbol) == 6:
                # 假设是A股代码
                if clean_symbol.startswith(('6', '5', '9')):
                    return MARKET_TYPE_A_SHARE
                elif clean_symbol.startswith(('0', '1', '2', '3')):
                    return MARKET_TYPE_A_SHARE
            elif len(clean_symbol) == 5 or (len(clean_symbol) == 4 and clean_symbol.startswith('0')):
                # 港股代码：5位数字，或者4位数字前导0
                return MARKET_TYPE_HK
        # 默认归为港股（因为腾讯是港股）
        return MARKET_TYPE_HK
    
    def _format_symbol(self, symbol: str, market: Optional[str] = None) -> str:
        """格式化代码为富途API需要的格式
        
        Args:
            symbol: 原始代码
            market: 市场类型，如果未提供则尝试从代码中识别
            
        Returns:
            str: 格式化后的代码
        """
        # 如果已经是标准格式，则直接返回
        if '.' in symbol and symbol.split('.')[0] in ['HK', 'US', 'SH', 'SZ']:
            return symbol
        
        # 获取市场类型
        if market is None:
            market = self._get_market_from_symbol(symbol)
        
        # 移除可能存在的前缀
        clean_symbol = symbol.split('.')[-1]
        
        # 根据市场类型添加前缀
        if market == MARKET_TYPE_HK:
            # 处理港股代码
            return f"HK.{clean_symbol.zfill(5)}"
        elif market == MARKET_TYPE_US:
            # 处理美股代码
            return f"US.{clean_symbol}"
        elif market == MARKET_TYPE_A_SHARE:
            # 处理A股代码
            if clean_symbol.startswith(('6', '5', '9')):
                return f"SH.{clean_symbol}"
            else:
                return f"SZ.{clean_symbol}"
        
        # 默认返回原始代码
        return symbol
    
    def get_kline_data(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """获取K线数据
        
        Args:
            symbol: 股票代码
            timeframe: 时间周期
            limit: 返回的K线数量
            
        Returns:
            pd.DataFrame: K线数据
        """
        try:
            formatted_symbol = self._format_symbol(symbol)
            logging.info(f"请求K线数据，格式化后的代码: {formatted_symbol}, 时间周期: {timeframe}")
            
            quote_ctx = self._get_quote_ctx()
            ktype = self._convert_ktype(timeframe)
            
            # 获取历史K线，富途API返回的是 (ret_code, data, if_req_data_forward)
            result = quote_ctx.request_history_kline(formatted_symbol, ktype=ktype, max_count=limit)
            
            # 根据返回值的个数解包
            if len(result) == 2:
                ret, data = result
            elif len(result) == 3:
                ret, data, _ = result
            else:
                logging.error(f"富途API返回值格式异常: {result}")
                return pd.DataFrame()
            
            if ret == ft.RET_OK:
                data = data.rename(columns={
                    'time_key': 'timestamp',
                    'open': 'open',
                    'high': 'high',
                    'low': 'low',
                    'close': 'close',
                    'volume': 'volume',
                    'turnover': 'turnover'
                })
                
                if 'timestamp' in data.columns:
                    data['timestamp'] = pd.to_datetime(data['timestamp'])
                    data = data.set_index('timestamp')
                
                return data
            else:
                logging.error(f"获取K线数据失败: {data}")
                return pd.DataFrame()
            
        except Exception as e:
            logging.error(f"获取K线数据异常: {e}")
            import traceback
            logging.error(traceback.format_exc())
            return pd.DataFrame()
    
    def get_ticker_info(self, symbol: str) -> Dict[str, Any]:
        """获取股票信息
        
        Args:
            symbol: 股票代码
            
        Returns:
            Dict: 股票信息
        """
        try:
            # 格式化代码
            formatted_symbol = self._format_symbol(symbol)
            
            # 获取行情上下文
            quote_ctx = self._get_quote_ctx()
            
            # 获取快照数据
            ret, data = quote_ctx.get_market_snapshot([formatted_symbol])
            
            if ret == ft.RET_OK and not data.empty:
                # 转换为字典
                info = data.iloc[0].to_dict()
                return info
            else:
                logging.error(f"获取股票信息失败: {data}")
                return {}
            
        except Exception as e:
            logging.error(f"获取股票信息异常: {e}")
            return {}
    
    def place_order(self, symbol: str, quantity: float, side: str, 
                   order_type: str = ORDER_TYPE_MARKET, price: Optional[float] = None) -> Dict[str, Any]:
        """下单
        
        Args:
            symbol: 股票代码
            quantity: 数量
            side: 买卖方向，buy或sell
            order_type: 订单类型，market或limit
            price: 价格，市价单可不填
            
        Returns:
            Dict: 订单信息
        """
        try:
            # 格式化代码
            formatted_symbol = self._format_symbol(symbol)
            
            # 获取市场类型
            market = self._get_market_from_symbol(formatted_symbol)
            
            # 获取对应的交易上下文
            trade_ctx = self.market_trade_ctx.get(market, self._get_hk_trade_ctx)()
            
            # 转换订单类型和方向
            ft_order_type = self._convert_order_type(order_type)
            ft_side = self._convert_order_side(side)
            
            # 下单
            ret, data = trade_ctx.place_order(
                code=formatted_symbol,
                qty=quantity,
                trd_side=ft_side,
                order_type=ft_order_type,
                price=price,
                trd_mkt=market
            )
            
            if ret and not data.empty:
                # 转换为字典
                order_info = data.iloc[0].to_dict()
                return order_info
            else:
                logging.error(f"下单失败: {data}")
                return {}
            
        except Exception as e:
            logging.error(f"下单异常: {e}")
            return {}
    
    def get_account_info(self, market: str = MARKET_TYPE_HK) -> Dict[str, Any]:
        """获取账户信息
        
        Args:
            market: 市场类型
            
        Returns:
            Dict: 账户信息
        """
        try:
            # 获取对应的交易上下文
            trade_ctx = self.market_trade_ctx.get(market, self._get_hk_trade_ctx)()
            
            # 获取账户信息
            ret, data = trade_ctx.get_account_info()
            
            if ret and not data.empty:
                # 转换为字典
                account_info = data.iloc[0].to_dict()
                return account_info
            else:
                logging.error(f"获取账户信息失败: {data}")
                return {}
            
        except Exception as e:
            logging.error(f"获取账户信息异常: {e}")
            return {}
    
    def get_positions(self, market: str = MARKET_TYPE_HK) -> pd.DataFrame:
        """获取持仓信息
        
        Args:
            market: 市场类型
            
        Returns:
            pd.DataFrame: 持仓信息
        """
        try:
            # 获取对应的交易上下文
            trade_ctx = self.market_trade_ctx.get(market, self._get_hk_trade_ctx)()
            
            # 获取持仓列表
            ret, data = trade_ctx.get_position_list()
            
            if ret:
                return data
            else:
                logging.error(f"获取持仓信息失败: {data}")
                return pd.DataFrame()
            
        except Exception as e:
            logging.error(f"获取持仓信息异常: {e}")
            return pd.DataFrame()
    
    def get_orders(self, market: str = MARKET_TYPE_HK) -> pd.DataFrame:
        """获取订单信息
        
        Args:
            market: 市场类型
            
        Returns:
            pd.DataFrame: 订单信息
        """
        try:
            # 获取对应的交易上下文
            trade_ctx = self.market_trade_ctx.get(market, self._get_hk_trade_ctx)()
            
            # 获取订单列表
            ret, data = trade_ctx.get_order_list()
            
            if ret:
                return data
            else:
                logging.error(f"获取订单信息失败: {data}")
                return pd.DataFrame()
            
        except Exception as e:
            logging.error(f"获取订单信息异常: {e}")
            return pd.DataFrame()
    
    def close(self):
        """关闭所有连接"""
        try:
            if self.quote_ctx and self.quote_ctx.connected:
                self.quote_ctx.close()
            
            if self.trade_ctx_hk and self.trade_ctx_hk.connected:
                self.trade_ctx_hk.close()
                
            if self.trade_ctx_us and self.trade_ctx_us.connected:
                self.trade_ctx_us.close()
                
            if self.trade_ctx_cn and self.trade_ctx_cn.connected:
                self.trade_ctx_cn.close()
                
        except Exception as e:
            logging.error(f"关闭连接异常: {e}")