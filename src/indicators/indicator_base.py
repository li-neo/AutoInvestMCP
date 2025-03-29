"""
技术指标基类，定义所有技术指标的通用接口
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np


class IndicatorBase(ABC):
    """技术指标基类"""
    
    def __init__(self, name: str):
        """初始化指标
        
        Args:
            name: 指标名称
        """
        self.name = name
    
    @abstractmethod
    def calculate(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """计算指标
        
        Args:
            data: 包含OHLCV数据的DataFrame
            **kwargs: 其他参数
            
        Returns:
            pd.DataFrame: 添加了指标列的DataFrame
        """
        pass
    
    @abstractmethod
    def get_signal(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """生成交易信号
        
        Args:
            data: 包含指标数据的DataFrame
            **kwargs: 其他参数
            
        Returns:
            pd.DataFrame: 添加了交易信号列的DataFrame
        """
        pass
    
    def get_description(self) -> str:
        """获取指标的描述
        
        Returns:
            str: 指标描述
        """
        return f"{self.name} 指标"


class MovingAverageBase(IndicatorBase):
    """移动平均线基类"""
    
    def __init__(self, name: str, window: int = 20, price_key: str = 'close'):
        """初始化移动平均指标
        
        Args:
            name: 指标名称
            window: 窗口大小
            price_key: 使用的价格列名，默认为收盘价
        """
        super().__init__(name)
        self.window = window
        self.price_key = price_key
        self.column_name = f"{name}_{window}"
    
    def get_signal(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """生成基于移动平均的交易信号
        
        Args:
            data: 包含指标数据的DataFrame
            **kwargs: 其他参数
                - short_window: 短期窗口，用于交叉信号
                - signal_type: 信号类型，可以是'cross'(交叉)或'trend'(趋势)
            
        Returns:
            pd.DataFrame: 添加了交易信号列的DataFrame
        """
        # 确保指标已经计算
        if self.column_name not in data.columns:
            data = self.calculate(data)
            
        signal_type = kwargs.get('signal_type', 'trend')
        signal_column = f"{self.name}_signal"
        
        if signal_type == 'cross' and 'short_window' in kwargs:
            # 交叉信号
            short_window = kwargs['short_window']
            short_column = f"{self.name}_{short_window}"
            
            # 确保短期指标已经计算
            if short_column not in data.columns:
                # 临时创建短期指标并计算
                temp_indicator = self.__class__(self.name, short_window, self.price_key)
                data = temp_indicator.calculate(data)
            
            # 计算交叉信号
            data[signal_column] = 0  # 默认无信号
            # 金叉：短期均线上穿长期均线
            data.loc[(data[short_column] > data[self.column_name]) & 
                     (data[short_column].shift(1) <= data[self.column_name].shift(1)), signal_column] = 1
            # 死叉：短期均线下穿长期均线
            data.loc[(data[short_column] < data[self.column_name]) & 
                     (data[short_column].shift(1) >= data[self.column_name].shift(1)), signal_column] = -1
        
        elif signal_type == 'trend':
            # 趋势信号
            data[signal_column] = 0  # 默认无信号
            
            # 价格上穿均线：买入信号
            data.loc[(data[self.price_key] > data[self.column_name]) & 
                     (data[self.price_key].shift(1) <= data[self.column_name].shift(1)), signal_column] = 1
            
            # 价格下穿均线：卖出信号
            data.loc[(data[self.price_key] < data[self.column_name]) & 
                     (data[self.price_key].shift(1) >= data[self.column_name].shift(1)), signal_column] = -1
        
        return data