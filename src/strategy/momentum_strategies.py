"""
动量策略实现，包括MACD交叉策略、均线交叉策略等
"""
from typing import Dict, List, Any, Optional
import pandas as pd

from src.strategy.strategy_base import StrategyBase
from config.constants import (
    INDICATOR_MA, INDICATOR_EMA, INDICATOR_MACD, INDICATOR_RSI,
    STRATEGY_MACD_CROSS, STRATEGY_MA_CROSS, STRATEGY_RSI_OVERBOUGHT
)


class MACDCrossStrategy(StrategyBase):
    """MACD交叉策略"""
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9,
                 price_key: str = 'close'):
        """初始化MACD交叉策略
        
        Args:
            fast_period: 快线周期
            slow_period: 慢线周期
            signal_period: 信号线周期
            price_key: 使用的价格列名
        """
        super().__init__(STRATEGY_MACD_CROSS)
        
        # 设置策略参数
        self.params = {
            'fast_period': fast_period,
            'slow_period': slow_period,
            'signal_period': signal_period,
            'price_key': price_key
        }
        
        # 添加所需指标
        self.add_indicator(
            INDICATOR_MACD,
            {'fast_period': fast_period, 'slow_period': slow_period, 'signal_period': signal_period, 'price_key': price_key},
            {'signal_type': 'cross'}
        )
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成MACD交叉信号
        
        Args:
            data: 包含指标的DataFrame
            
        Returns:
            pd.DataFrame: 添加了策略信号的DataFrame
        """
        data = data.copy()
        
        # 确保包含MACD信号
        if 'macd_cross_signal' not in data.columns:
            raise ValueError("数据中缺少MACD交叉信号列，请确保已调用prepare_data()")
        
        # MACD信号直接作为策略信号
        data['signal'] = data['macd_cross_signal']
        
        return data
    
    def get_description(self) -> str:
        """获取策略的描述
        
        Returns:
            str: 策略描述
        """
        return f"MACD交叉策略(快线={self.params['fast_period']}, 慢线={self.params['slow_period']}, 信号线={self.params['signal_period']})"


class MACrossStrategy(StrategyBase):
    """均线交叉策略"""
    
    def __init__(self, fast_period: int = 5, slow_period: int = 20, ma_type: str = INDICATOR_MA,
                 price_key: str = 'close'):
        """初始化均线交叉策略
        
        Args:
            fast_period: 快线周期
            slow_period: 慢线周期
            ma_type: 移动平均线类型，可以是INDICATOR_MA或INDICATOR_EMA
            price_key: 使用的价格列名
        """
        super().__init__(STRATEGY_MA_CROSS)
        
        # 设置策略参数
        self.params = {
            'fast_period': fast_period,
            'slow_period': slow_period,
            'ma_type': ma_type,
            'price_key': price_key
        }
        
        # 添加所需指标
        self.add_indicator(
            ma_type,
            {'window': slow_period, 'price_key': price_key},
            {'signal_type': 'cross', 'short_window': fast_period}
        )
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成均线交叉信号
        
        Args:
            data: 包含指标的DataFrame
            
        Returns:
            pd.DataFrame: 添加了策略信号的DataFrame
        """
        data = data.copy()
        
        # 获取MA类型
        ma_type = self.params['ma_type']
        signal_column = f"{ma_type}_signal"
        
        # 确保包含均线信号
        if signal_column not in data.columns:
            raise ValueError(f"数据中缺少均线信号列{signal_column}，请确保已调用prepare_data()")
        
        # 均线信号直接作为策略信号
        data['signal'] = data[signal_column]
        
        return data
    
    def get_description(self) -> str:
        """获取策略的描述
        
        Returns:
            str: 策略描述
        """
        ma_type_name = "简单移动平均线" if self.params['ma_type'] == INDICATOR_MA else "指数移动平均线"
        return f"均线交叉策略({ma_type_name}, 快线={self.params['fast_period']}, 慢线={self.params['slow_period']})"


class RSIOverboughtStrategy(StrategyBase):
    """RSI超买超卖策略"""
    
    def __init__(self, rsi_period: int = 14, overbought: int = 70, oversold: int = 30,
                 price_key: str = 'close'):
        """初始化RSI超买超卖策略
        
        Args:
            rsi_period: RSI周期
            overbought: 超买阈值
            oversold: 超卖阈值
            price_key: 使用的价格列名
        """
        super().__init__(STRATEGY_RSI_OVERBOUGHT)
        
        # 设置策略参数
        self.params = {
            'rsi_period': rsi_period,
            'overbought': overbought,
            'oversold': oversold,
            'price_key': price_key
        }
        
        # 添加所需指标
        self.add_indicator(
            INDICATOR_RSI,
            {'window': rsi_period, 'price_key': price_key},
            {'signal_type': 'level', 'overbought': overbought, 'oversold': oversold}
        )
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成RSI超买超卖信号
        
        Args:
            data: 包含指标的DataFrame
            
        Returns:
            pd.DataFrame: 添加了策略信号的DataFrame
        """
        data = data.copy()
        
        # 确保包含RSI信号
        rsi_column = f"rsi_{self.params['rsi_period']}"
        signal_column = f"{rsi_column}_level_signal"
        
        if signal_column not in data.columns:
            raise ValueError(f"数据中缺少RSI信号列{signal_column}，请确保已调用prepare_data()")
        
        # RSI信号直接作为策略信号
        data['signal'] = data[signal_column]
        
        return data
    
    def get_description(self) -> str:
        """获取策略的描述
        
        Returns:
            str: 策略描述
        """
        return f"RSI超买超卖策略(周期={self.params['rsi_period']}, 超买={self.params['overbought']}, 超卖={self.params['oversold']})"