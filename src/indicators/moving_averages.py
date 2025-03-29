"""
移动平均线指标实现
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List

from src.indicators.indicator_base import MovingAverageBase


class SimpleMovingAverage(MovingAverageBase):
    """简单移动平均线(SMA)"""
    
    def __init__(self, window: int = 20, price_key: str = 'close'):
        """初始化简单移动平均线
        
        Args:
            window: 窗口大小
            price_key: 使用的价格列名，默认为收盘价
        """
        super().__init__('ma', window, price_key)
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """计算简单移动平均线
        
        Args:
            data: 包含OHLCV数据的DataFrame
            **kwargs: 其他参数
            
        Returns:
            pd.DataFrame: 添加了MA指标列的DataFrame
        """
        data = data.copy()
        data[self.column_name] = data[self.price_key].rolling(window=self.window).mean()
        return data
    
    def get_description(self) -> str:
        """获取指标的描述
        
        Returns:
            str: 指标描述
        """
        return f"简单移动平均线(MA)，周期={self.window}"


class ExponentialMovingAverage(MovingAverageBase):
    """指数移动平均线(EMA)"""
    
    def __init__(self, window: int = 20, price_key: str = 'close'):
        """初始化指数移动平均线
        
        Args:
            window: 窗口大小
            price_key: 使用的价格列名，默认为收盘价
        """
        super().__init__('ema', window, price_key)
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """计算指数移动平均线
        
        Args:
            data: 包含OHLCV数据的DataFrame
            **kwargs: 其他参数
            
        Returns:
            pd.DataFrame: 添加了EMA指标列的DataFrame
        """
        data = data.copy()
        data[self.column_name] = data[self.price_key].ewm(span=self.window, adjust=False).mean()
        return data
    
    def get_description(self) -> str:
        """获取指标的描述
        
        Returns:
            str: 指标描述
        """
        return f"指数移动平均线(EMA)，周期={self.window}"


class MACD(IndicatorBase):
    """MACD指标"""
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9, price_key: str = 'close'):
        """初始化MACD指标
        
        Args:
            fast_period: 快线周期
            slow_period: 慢线周期
            signal_period: 信号线周期
            price_key: 使用的价格列名，默认为收盘价
        """
        super().__init__('macd')
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.price_key = price_key
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """计算MACD指标
        
        Args:
            data: 包含OHLCV数据的DataFrame
            **kwargs: 其他参数
            
        Returns:
            pd.DataFrame: 添加了MACD指标列的DataFrame
        """
        data = data.copy()
        
        # 计算快线EMA
        fast_ema = data[self.price_key].ewm(span=self.fast_period, adjust=False).mean()
        
        # 计算慢线EMA
        slow_ema = data[self.price_key].ewm(span=self.slow_period, adjust=False).mean()
        
        # 计算MACD线
        data['macd'] = fast_ema - slow_ema
        
        # 计算信号线
        data['macd_signal'] = data['macd'].ewm(span=self.signal_period, adjust=False).mean()
        
        # 计算柱状图
        data['macd_hist'] = data['macd'] - data['macd_signal']
        
        return data
    
    def get_signal(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """生成基于MACD的交易信号
        
        Args:
            data: 包含指标数据的DataFrame
            **kwargs: 其他参数
                - signal_type: 信号类型，可以是'cross'(交叉)或'divergence'(背离)
            
        Returns:
            pd.DataFrame: 添加了交易信号列的DataFrame
        """
        # 确保指标已经计算
        if 'macd' not in data.columns:
            data = self.calculate(data)
            
        signal_type = kwargs.get('signal_type', 'cross')
        
        if signal_type == 'cross':
            # 计算MACD交叉信号
            data['macd_cross_signal'] = 0  # 默认无信号
            
            # 金叉：MACD线上穿信号线
            data.loc[(data['macd'] > data['macd_signal']) & 
                     (data['macd'].shift(1) <= data['macd_signal'].shift(1)), 'macd_cross_signal'] = 1
            
            # 死叉：MACD线下穿信号线
            data.loc[(data['macd'] < data['macd_signal']) & 
                     (data['macd'].shift(1) >= data['macd_signal'].shift(1)), 'macd_cross_signal'] = -1
        
        elif signal_type == 'divergence':
            # 背离信号需要更复杂的计算
            # 这里提供一个简化版本
            data['macd_divergence_signal'] = 0  # 默认无信号
            
            # 查找局部极值
            for i in range(2, len(data) - 2):
                # 价格出现高点但MACD没有创新高 -> 顶背离
                if (data[self.price_key].iloc[i] > data[self.price_key].iloc[i-1] and 
                    data[self.price_key].iloc[i] > data[self.price_key].iloc[i+1] and
                    data['macd'].iloc[i] < data['macd'].iloc[i-2]):
                    data['macd_divergence_signal'].iloc[i] = -1
                
                # 价格出现低点但MACD没有创新低 -> 底背离
                elif (data[self.price_key].iloc[i] < data[self.price_key].iloc[i-1] and 
                      data[self.price_key].iloc[i] < data[self.price_key].iloc[i+1] and
                      data['macd'].iloc[i] > data['macd'].iloc[i-2]):
                    data['macd_divergence_signal'].iloc[i] = 1
        
        return data
    
    def get_description(self) -> str:
        """获取指标的描述
        
        Returns:
            str: 指标描述
        """
        return f"MACD指标，快线周期={self.fast_period}，慢线周期={self.slow_period}，信号线周期={self.signal_period}"


class BollingerBands(IndicatorBase):
    """布林带指标"""
    
    def __init__(self, window: int = 20, std_dev: float = 2.0, price_key: str = 'close'):
        """初始化布林带指标
        
        Args:
            window: 窗口大小
            std_dev: 标准差乘数
            price_key: 使用的价格列名，默认为收盘价
        """
        super().__init__('bollinger')
        self.window = window
        self.std_dev = std_dev
        self.price_key = price_key
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """计算布林带指标
        
        Args:
            data: 包含OHLCV数据的DataFrame
            **kwargs: 其他参数
            
        Returns:
            pd.DataFrame: 添加了布林带指标列的DataFrame
        """
        data = data.copy()
        
        # 计算移动平均线
        data['bollinger_ma'] = data[self.price_key].rolling(window=self.window).mean()
        
        # 计算标准差
        data['bollinger_std'] = data[self.price_key].rolling(window=self.window).std()
        
        # 计算上轨和下轨
        data['bollinger_upper'] = data['bollinger_ma'] + (data['bollinger_std'] * self.std_dev)
        data['bollinger_lower'] = data['bollinger_ma'] - (data['bollinger_std'] * self.std_dev)
        
        # 计算带宽
        data['bollinger_bandwidth'] = (data['bollinger_upper'] - data['bollinger_lower']) / data['bollinger_ma']
        
        # 计算百分比B
        data['bollinger_b'] = (data[self.price_key] - data['bollinger_lower']) / (data['bollinger_upper'] - data['bollinger_lower'])
        
        return data
    
    def get_signal(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """生成基于布林带的交易信号
        
        Args:
            data: 包含指标数据的DataFrame
            **kwargs: 其他参数
                - signal_type: 信号类型，可以是'breakout'(突破)或'mean_reversion'(均值回归)
            
        Returns:
            pd.DataFrame: 添加了交易信号列的DataFrame
        """
        # 确保指标已经计算
        if 'bollinger_upper' not in data.columns:
            data = self.calculate(data)
            
        signal_type = kwargs.get('signal_type', 'breakout')
        
        if signal_type == 'breakout':
            # 计算突破信号
            data['bollinger_breakout_signal'] = 0  # 默认无信号
            
            # 价格上穿上轨：买入信号
            data.loc[(data[self.price_key] > data['bollinger_upper']) & 
                     (data[self.price_key].shift(1) <= data['bollinger_upper'].shift(1)), 'bollinger_breakout_signal'] = 1
            
            # 价格下穿下轨：卖出信号
            data.loc[(data[self.price_key] < data['bollinger_lower']) & 
                     (data[self.price_key].shift(1) >= data['bollinger_lower'].shift(1)), 'bollinger_breakout_signal'] = -1
        
        elif signal_type == 'mean_reversion':
            # 计算均值回归信号
            data['bollinger_mean_reversion_signal'] = 0  # 默认无信号
            
            # 价格触及上轨：卖出信号
            data.loc[data[self.price_key] >= data['bollinger_upper'], 'bollinger_mean_reversion_signal'] = -1
            
            # 价格触及下轨：买入信号
            data.loc[data[self.price_key] <= data['bollinger_lower'], 'bollinger_mean_reversion_signal'] = 1
        
        return data
    
    def get_description(self) -> str:
        """获取指标的描述
        
        Returns:
            str: 指标描述
        """
        return f"布林带指标，周期={self.window}，标准差乘数={self.std_dev}"