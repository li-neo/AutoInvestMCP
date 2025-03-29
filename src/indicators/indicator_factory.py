"""
指标工厂，用于创建和管理各种技术指标
"""
from typing import Dict, List, Any, Optional, Union, Type

import pandas as pd

from src.indicators.indicator_base import IndicatorBase
from src.indicators.moving_averages import SimpleMovingAverage, ExponentialMovingAverage, MACD, BollingerBands
from src.indicators.oscillators import RSI, KDJ, VolumeProfile
from config.constants import (
    INDICATOR_MA, INDICATOR_EMA, INDICATOR_MACD, INDICATOR_RSI,
    INDICATOR_BOLLINGER, INDICATOR_KDJ, INDICATOR_VOLUME
)


class IndicatorFactory:
    """指标工厂，用于创建和管理各种技术指标"""
    
    # 指标类型映射
    INDICATOR_MAP = {
        INDICATOR_MA: SimpleMovingAverage,
        INDICATOR_EMA: ExponentialMovingAverage,
        INDICATOR_MACD: MACD,
        INDICATOR_RSI: RSI,
        INDICATOR_BOLLINGER: BollingerBands,
        INDICATOR_KDJ: KDJ,
        INDICATOR_VOLUME: VolumeProfile
    }
    
    @classmethod
    def create_indicator(cls, indicator_type: str, **kwargs) -> Optional[IndicatorBase]:
        """创建指标实例
        
        Args:
            indicator_type: 指标类型
            **kwargs: 传递给指标构造函数的参数
            
        Returns:
            IndicatorBase: 指标实例，如果类型不支持则返回None
        """
        indicator_class = cls.INDICATOR_MAP.get(indicator_type)
        if not indicator_class:
            raise ValueError(f"不支持的指标类型: {indicator_type}")
        
        return indicator_class(**kwargs)
    
    @classmethod
    def get_all_indicator_types(cls) -> List[str]:
        """获取所有支持的指标类型
        
        Returns:
            List[str]: 指标类型列表
        """
        return list(cls.INDICATOR_MAP.keys())
    
    @classmethod
    def calculate_indicators(cls, data: pd.DataFrame, indicators: List[Dict[str, Any]]) -> pd.DataFrame:
        """计算多个指标
        
        Args:
            data: 原始数据DataFrame
            indicators: 指标配置列表，每个元素是一个字典，包含以下字段：
                - type: 指标类型
                - params: 指标参数字典
        
        Returns:
            pd.DataFrame: 添加了指标列的DataFrame
        """
        result = data.copy()
        
        for indicator_config in indicators:
            indicator_type = indicator_config.get('type')
            params = indicator_config.get('params', {})
            
            try:
                indicator = cls.create_indicator(indicator_type, **params)
                result = indicator.calculate(result)
            except Exception as e:
                print(f"计算指标 {indicator_type} 失败: {e}")
                
        return result
    
    @classmethod
    def get_indicator_signals(cls, data: pd.DataFrame, indicators: List[Dict[str, Any]]) -> pd.DataFrame:
        """获取多个指标的信号
        
        Args:
            data: 包含指标数据的DataFrame
            indicators: 指标配置列表，每个元素是一个字典，包含以下字段：
                - type: 指标类型
                - params: 指标参数字典
                - signal_params: 信号参数字典
        
        Returns:
            pd.DataFrame: 添加了信号列的DataFrame
        """
        result = data.copy()
        
        for indicator_config in indicators:
            indicator_type = indicator_config.get('type')
            params = indicator_config.get('params', {})
            signal_params = indicator_config.get('signal_params', {})
            
            try:
                indicator = cls.create_indicator(indicator_type, **params)
                
                # 确保指标已计算
                if not any(col.startswith(indicator.name) for col in result.columns):
                    result = indicator.calculate(result)
                
                # 计算信号
                result = indicator.get_signal(result, **signal_params)
            except Exception as e:
                print(f"获取指标 {indicator_type} 的信号失败: {e}")
                
        return result