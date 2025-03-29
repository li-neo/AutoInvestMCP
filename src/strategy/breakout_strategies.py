"""
突破策略实现，包括布林带突破策略、支撑阻力突破策略等
"""
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

from src.strategy.strategy_base import StrategyBase
from config.constants import (
    INDICATOR_BOLLINGER, INDICATOR_MA, INDICATOR_EMA,
    STRATEGY_BREAKOUT
)


class BollingerBreakoutStrategy(StrategyBase):
    """布林带突破策略"""
    
    def __init__(self, window: int = 20, std_dev: float = 2.0, price_key: str = 'close',
                 breakout_type: str = 'breakout'):
        """初始化布林带突破策略
        
        Args:
            window: 移动平均窗口大小
            std_dev: 标准差乘数
            price_key: 使用的价格列名
            breakout_type: 突破类型，'breakout'(突破)或'mean_reversion'(均值回归)
        """
        super().__init__(STRATEGY_BREAKOUT)
        
        # 设置策略参数
        self.params = {
            'window': window,
            'std_dev': std_dev,
            'price_key': price_key,
            'breakout_type': breakout_type
        }
        
        # 添加所需指标
        self.add_indicator(
            INDICATOR_BOLLINGER,
            {'window': window, 'std_dev': std_dev, 'price_key': price_key},
            {'signal_type': breakout_type}
        )
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成布林带突破信号
        
        Args:
            data: 包含指标的DataFrame
            
        Returns:
            pd.DataFrame: 添加了策略信号的DataFrame
        """
        data = data.copy()
        
        # 获取信号类型
        breakout_type = self.params['breakout_type']
        signal_column = f"bollinger_{breakout_type}_signal"
        
        # 确保包含布林带信号
        if signal_column not in data.columns:
            raise ValueError(f"数据中缺少布林带信号列{signal_column}，请确保已调用prepare_data()")
        
        # 布林带信号直接作为策略信号
        data['signal'] = data[signal_column]
        
        return data
    
    def get_description(self) -> str:
        """获取策略的描述
        
        Returns:
            str: 策略描述
        """
        breakout_type_name = "突破" if self.params['breakout_type'] == 'breakout' else "均值回归"
        return f"布林带{breakout_type_name}策略(周期={self.params['window']}, 标准差倍数={self.params['std_dev']})"


class HighLowBreakoutStrategy(StrategyBase):
    """高低点突破策略"""
    
    def __init__(self, lookback_period: int = 20, breakout_threshold: float = 0.0,
                 confirmation_days: int = 1):
        """初始化高低点突破策略
        
        Args:
            lookback_period: 寻找高低点的回看周期
            breakout_threshold: 突破阈值百分比，例如0.01表示需要突破1%才产生信号
            confirmation_days: 确认天数，连续突破几天才产生信号
        """
        super().__init__(STRATEGY_BREAKOUT)
        
        # 设置策略参数
        self.params = {
            'lookback_period': lookback_period,
            'breakout_threshold': breakout_threshold,
            'confirmation_days': confirmation_days
        }
    
    def prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """准备数据，计算最近高低点
        
        Args:
            data: 原始数据DataFrame
            
        Returns:
            pd.DataFrame: 添加了高低点的DataFrame
        """
        data = data.copy()
        lookback = self.params['lookback_period']
        
        # 计算最近的高点和低点
        data['recent_high'] = data['high'].rolling(window=lookback).max()
        data['recent_low'] = data['low'].rolling(window=lookback).min()
        
        # 带阈值的高点和低点
        threshold = self.params['breakout_threshold']
        if threshold > 0:
            data['high_with_threshold'] = data['recent_high'] * (1 + threshold)
            data['low_with_threshold'] = data['recent_low'] * (1 - threshold)
        else:
            data['high_with_threshold'] = data['recent_high']
            data['low_with_threshold'] = data['recent_low']
        
        return data
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成高低点突破信号
        
        Args:
            data: 包含高低点的DataFrame
            
        Returns:
            pd.DataFrame: 添加了策略信号的DataFrame
        """
        data = data.copy()
        
        # 确保包含高低点
        required_columns = ['recent_high', 'recent_low', 'high_with_threshold', 'low_with_threshold']
        if not all(col in data.columns for col in required_columns):
            data = self.prepare_data(data)
        
        # 计算突破信号
        data['upward_breakout'] = data['close'] > data['high_with_threshold'].shift(1)
        data['downward_breakout'] = data['close'] < data['low_with_threshold'].shift(1)
        
        # 初始化信号列
        data['signal'] = 0
        
        # 根据确认天数生成信号
        confirmation_days = self.params['confirmation_days']
        
        if confirmation_days <= 1:
            # 不需要确认的情况
            data.loc[data['upward_breakout'], 'signal'] = 1
            data.loc[data['downward_breakout'], 'signal'] = -1
        else:
            # 需要连续确认的情况
            for i in range(confirmation_days, len(data)):
                # 连续上行突破
                if all(data['upward_breakout'].iloc[i-confirmation_days+1:i+1]):
                    data['signal'].iloc[i] = 1
                
                # 连续下行突破
                if all(data['downward_breakout'].iloc[i-confirmation_days+1:i+1]):
                    data['signal'].iloc[i] = -1
        
        return data
    
    def get_description(self) -> str:
        """获取策略的描述
        
        Returns:
            str: 策略描述
        """
        threshold_str = f"{self.params['breakout_threshold'] * 100}%" if self.params['breakout_threshold'] > 0 else "0%"
        confirmation_str = "" if self.params['confirmation_days'] <= 1 else f"，需要连续{self.params['confirmation_days']}天确认"
        return f"高低点突破策略(周期={self.params['lookback_period']}, 阈值={threshold_str}{confirmation_str})"


class VolumeBreakoutStrategy(StrategyBase):
    """量价突破策略"""
    
    def __init__(self, price_lookback: int = 20, volume_lookback: int = 20, 
                 price_threshold: float = 0.0, volume_threshold: float = 1.5):
        """初始化量价突破策略
        
        Args:
            price_lookback: 价格回看周期
            volume_lookback: 成交量回看周期
            price_threshold: 价格突破阈值百分比
            volume_threshold: 成交量突破倍数
        """
        super().__init__(STRATEGY_BREAKOUT)
        
        # 设置策略参数
        self.params = {
            'price_lookback': price_lookback,
            'volume_lookback': volume_lookback,
            'price_threshold': price_threshold,
            'volume_threshold': volume_threshold
        }
    
    def prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """准备数据，计算价格和成交量的高点
        
        Args:
            data: 原始数据DataFrame
            
        Returns:
            pd.DataFrame: 添加了价格和成交量高点的DataFrame
        """
        data = data.copy()
        price_lookback = self.params['price_lookback']
        volume_lookback = self.params['volume_lookback']
        
        # 计算最近的价格高点
        data['price_high'] = data['high'].rolling(window=price_lookback).max()
        
        # 计算成交量移动平均
        data['volume_ma'] = data['volume'].rolling(window=volume_lookback).mean()
        
        # 带阈值的价格高点
        price_threshold = self.params['price_threshold']
        if price_threshold > 0:
            data['price_high_with_threshold'] = data['price_high'] * (1 + price_threshold)
        else:
            data['price_high_with_threshold'] = data['price_high']
        
        return data
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成量价突破信号
        
        Args:
            data: 包含价格和成交量指标的DataFrame
            
        Returns:
            pd.DataFrame: 添加了策略信号的DataFrame
        """
        data = data.copy()
        
        # 确保包含价格和成交量指标
        required_columns = ['price_high', 'volume_ma', 'price_high_with_threshold']
        if not all(col in data.columns for col in required_columns):
            data = self.prepare_data(data)
        
        # 初始化信号列
        data['signal'] = 0
        
        # 计算量价突破信号
        volume_threshold = self.params['volume_threshold']
        
        # 同时满足价格突破和成交量放大的条件
        price_breakout = data['close'] > data['price_high_with_threshold'].shift(1)
        volume_breakout = data['volume'] > data['volume_ma'].shift(1) * volume_threshold
        
        # 生成买入信号
        data.loc[price_breakout & volume_breakout, 'signal'] = 1
        
        # 价格跌破最近低点可以作为卖出信号
        data['price_low'] = data['low'].rolling(window=self.params['price_lookback']).min()
        price_breakdown = data['close'] < data['price_low'].shift(1)
        data.loc[price_breakdown, 'signal'] = -1
        
        return data
    
    def get_description(self) -> str:
        """获取策略的描述
        
        Returns:
            str: 策略描述
        """
        price_threshold_str = f"{self.params['price_threshold'] * 100}%" if self.params['price_threshold'] > 0 else "0%"
        return f"量价突破策略(价格周期={self.params['price_lookback']}, 价格阈值={price_threshold_str}, 成交量周期={self.params['volume_lookback']}, 成交量阈值={self.params['volume_threshold']}倍)"