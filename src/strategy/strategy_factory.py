"""
策略工厂，用于创建和管理各种交易策略
"""
from typing import Dict, List, Any, Optional, Union, Type

from src.strategy.strategy_base import StrategyBase
from src.strategy.momentum_strategies import MACDCrossStrategy, MACrossStrategy, RSIOverboughtStrategy
from src.strategy.breakout_strategies import BollingerBreakoutStrategy, HighLowBreakoutStrategy, VolumeBreakoutStrategy
from src.strategy.grid_strategies import GridStrategy, DynamicGridStrategy
from config.constants import (
    STRATEGY_MACD_CROSS, STRATEGY_MA_CROSS, STRATEGY_RSI_OVERBOUGHT,
    STRATEGY_BREAKOUT, STRATEGY_GRID
)


class StrategyFactory:
    """策略工厂，用于创建和管理各种交易策略"""
    
    # 策略类型映射
    STRATEGY_MAP = {
        STRATEGY_MACD_CROSS: MACDCrossStrategy,
        STRATEGY_MA_CROSS: MACrossStrategy,
        STRATEGY_RSI_OVERBOUGHT: RSIOverboughtStrategy,
        STRATEGY_BREAKOUT: {
            'bollinger': BollingerBreakoutStrategy,
            'high_low': HighLowBreakoutStrategy,
            'volume': VolumeBreakoutStrategy
        },
        STRATEGY_GRID: {
            'fixed': GridStrategy,
            'dynamic': DynamicGridStrategy
        }
    }
    
    @classmethod
    def create_strategy(cls, strategy_type: str, subtype: str = None, **kwargs) -> Optional[StrategyBase]:
        """创建策略实例
        
        Args:
            strategy_type: 策略类型
            subtype: 子类型，对于有多个实现的策略类型
            **kwargs: 传递给策略构造函数的参数
            
        Returns:
            StrategyBase: 策略实例，如果类型不支持则返回None
        """
        strategy_class = None
        
        if strategy_type in cls.STRATEGY_MAP:
            if isinstance(cls.STRATEGY_MAP[strategy_type], dict):
                # 有子类型的情况
                if not subtype:
                    # 如果没有指定子类型，使用第一个
                    subtype = next(iter(cls.STRATEGY_MAP[strategy_type]))
                
                strategy_class = cls.STRATEGY_MAP[strategy_type].get(subtype)
            else:
                # 没有子类型的情况
                strategy_class = cls.STRATEGY_MAP[strategy_type]
        
        if not strategy_class:
            raise ValueError(f"不支持的策略类型: {strategy_type}{f'/{subtype}' if subtype else ''}")
        
        return strategy_class(**kwargs)
    
    @classmethod
    def get_all_strategy_types(cls) -> Dict[str, Union[Type, Dict[str, Type]]]:
        """获取所有支持的策略类型
        
        Returns:
            Dict: 策略类型和子类型字典
        """
        return cls.STRATEGY_MAP
    
    @classmethod
    def get_strategy_params(cls, strategy_type: str, subtype: str = None) -> Dict[str, Any]:
        """获取策略的默认参数
        
        Args:
            strategy_type: 策略类型
            subtype: 子类型，对于有多个实现的策略类型
            
        Returns:
            Dict: 策略默认参数
        """
        strategy_class = None
        
        if strategy_type in cls.STRATEGY_MAP:
            if isinstance(cls.STRATEGY_MAP[strategy_type], dict):
                # 有子类型的情况
                if not subtype:
                    # 如果没有指定子类型，使用第一个
                    subtype = next(iter(cls.STRATEGY_MAP[strategy_type]))
                
                strategy_class = cls.STRATEGY_MAP[strategy_type].get(subtype)
            else:
                # 没有子类型的情况
                strategy_class = cls.STRATEGY_MAP[strategy_type]
        
        if not strategy_class:
            raise ValueError(f"不支持的策略类型: {strategy_type}{f'/{subtype}' if subtype else ''}")
        
        # 创建一个示例实例来获取参数
        # 需要考虑不同策略需要不同的初始化参数
        try:
            if strategy_type == STRATEGY_GRID and subtype == 'fixed':
                instance = strategy_class(100.0, 80.0, 5)
            elif strategy_type == STRATEGY_GRID and subtype == 'dynamic':
                instance = strategy_class(100.0)
            else:
                instance = strategy_class()
            
            return instance.params
        except Exception as e:
            print(f"获取策略参数失败: {e}")
            return {}