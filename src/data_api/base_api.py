"""
数据API的基类，定义了所有数据源API需要实现的接口
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import pandas as pd


class BaseAPI(ABC):
    """所有数据API的基类，定义了标准接口方法"""
    
    @abstractmethod
    def connect(self) -> bool:
        """连接到API服务
        
        Returns:
            bool: 连接是否成功
        """
        pass
    
    @abstractmethod
    def get_market_data(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """获取市场行情数据
        
        Args:
            symbol: 交易对/股票代码
            timeframe: 时间周期
            limit: 获取的K线数量
            
        Returns:
            pandas.DataFrame: 市场数据，包含OHLCV等信息
        """
        pass
    
    @abstractmethod
    def get_ticker_info(self, symbol: str) -> Dict[str, Any]:
        """获取交易对/股票的基本信息
        
        Args:
            symbol: 交易对/股票代码
            
        Returns:
            Dict: 包含交易对/股票基本信息的字典
        """
        pass
    
    @abstractmethod
    def get_symbols(self, market: Optional[str] = None) -> List[str]:
        """获取可交易的所有交易对/股票
        
        Args:
            market: 可选，指定市场
            
        Returns:
            List[str]: 交易对/股票代码列表
        """
        pass
    
    @abstractmethod
    def place_order(self, symbol: str, order_type: str, side: str, 
                    amount: float, price: Optional[float] = None) -> Dict[str, Any]:
        """下单交易
        
        Args:
            symbol: 交易对/股票代码
            order_type: 订单类型，如market、limit等
            side: 交易方向，buy或sell
            amount: 交易数量
            price: 交易价格，对于市价单可为None
            
        Returns:
            Dict: 订单信息
        """
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """查询订单状态
        
        Args:
            order_id: 订单ID
            
        Returns:
            Dict: 订单状态信息
        """
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """取消订单
        
        Args:
            order_id: 订单ID
            
        Returns:
            bool: 取消是否成功
        """
        pass
    
    @abstractmethod
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息
        
        Returns:
            Dict: 账户信息，包括余额等
        """
        pass