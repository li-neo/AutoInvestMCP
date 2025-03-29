"""
测试交易策略模块
"""
import os
import sys
import unittest
import pandas as pd
import numpy as np

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.strategy.strategy_factory import StrategyFactory
from src.strategy.momentum_strategies import MACDCrossStrategy, MACrossStrategy, RSIOverboughtStrategy
from src.strategy.breakout_strategies import BollingerBreakoutStrategy, HighLowBreakoutStrategy
from src.strategy.grid_strategies import GridStrategy
from config.constants import (
    STRATEGY_MACD_CROSS, STRATEGY_MA_CROSS, STRATEGY_RSI_OVERBOUGHT,
    STRATEGY_BREAKOUT, STRATEGY_GRID
)


class TestStrategies(unittest.TestCase):
    """测试交易策略"""
    
    def setUp(self):
        """设置测试环境"""
        # 创建模拟的OHLCV数据
        np.random.seed(42)
        
        # 创建200条记录的模拟数据
        n = 200
        dates = pd.date_range('2023-01-01', periods=n)
        
        # 生成随机价格数据，使其具有一定的趋势和波动
        price = 100.0
        prices = []
        for _ in range(n):
            change = np.random.normal(0, 1)
            # 添加轻微的趋势
            trend = 0.05 * np.sin(np.pi * _ / 30)
            price += change + trend
            prices.append(max(price, 50))  # 确保价格不低于50
        
        close = np.array(prices)
        open_prices = close * (1 + np.random.normal(0, 0.01, n))
        high = np.maximum(close, open_prices) * (1 + np.random.normal(0, 0.005, n))
        low = np.minimum(close, open_prices) * (1 - np.random.normal(0, 0.005, n))
        volume = np.random.normal(1000000, 200000, n) * (1 + 0.1 * np.random.normal(0, 1, n))
        volume = np.abs(volume)
        
        # 创建DataFrame
        self.data = pd.DataFrame({
            'open': open_prices,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        }, index=dates)
    
    def test_macd_cross_strategy(self):
        """测试MACD交叉策略"""
        # 创建策略实例
        strategy = MACDCrossStrategy()
        
        # 准备数据
        data = strategy.prepare_data(self.data)
        
        # 生成信号
        result = strategy.generate_signals(data)
        
        # 验证结果
        self.assertIn('signal', result.columns)
        
        # 统计买入和卖出信号数量
        buy_signals = (result['signal'] == 1).sum()
        sell_signals = (result['signal'] == -1).sum()
        
        # 应该有一些买入和卖出信号
        self.assertGreater(buy_signals, 0)
        self.assertGreater(sell_signals, 0)
    
    def test_ma_cross_strategy(self):
        """测试均线交叉策略"""
        # 创建策略实例
        strategy = MACrossStrategy(fast_period=5, slow_period=20)
        
        # 准备数据
        data = strategy.prepare_data(self.data)
        
        # 生成信号
        result = strategy.generate_signals(data)
        
        # 验证结果
        self.assertIn('signal', result.columns)
        
        # 统计买入和卖出信号数量
        buy_signals = (result['signal'] == 1).sum()
        sell_signals = (result['signal'] == -1).sum()
        
        # 应该有一些买入和卖出信号
        self.assertGreater(buy_signals, 0)
        self.assertGreater(sell_signals, 0)
    
    def test_rsi_strategy(self):
        """测试RSI策略"""
        # 创建策略实例
        strategy = RSIOverboughtStrategy(rsi_period=14, overbought=70, oversold=30)
        
        # 准备数据
        data = strategy.prepare_data(self.data)
        
        # 生成信号
        result = strategy.generate_signals(data)
        
        # 验证结果
        self.assertIn('signal', result.columns)
    
    def test_bollinger_breakout_strategy(self):
        """测试布林带突破策略"""
        # 创建策略实例
        strategy = BollingerBreakoutStrategy(window=20, std_dev=2.0)
        
        # 准备数据
        data = strategy.prepare_data(self.data)
        
        # 生成信号
        result = strategy.generate_signals(data)
        
        # 验证结果
        self.assertIn('signal', result.columns)
    
    def test_grid_strategy(self):
        """测试网格策略"""
        # 创建策略实例
        current_price = self.data['close'].mean()
        strategy = GridStrategy(upper_price=current_price * 1.2, 
                               lower_price=current_price * 0.8, 
                               grid_num=5)
        
        # 准备数据
        data = strategy.prepare_data(self.data)
        
        # 生成信号
        result = strategy.generate_signals(data)
        
        # 验证结果
        self.assertIn('signal', result.columns)
    
    def test_strategy_factory(self):
        """测试策略工厂"""
        # 测试创建不同类型的策略
        strategies = [
            (STRATEGY_MACD_CROSS, None, {}),
            (STRATEGY_MA_CROSS, None, {'fast_period': 5, 'slow_period': 20}),
            (STRATEGY_RSI_OVERBOUGHT, None, {'rsi_period': 14}),
            (STRATEGY_BREAKOUT, 'bollinger', {'window': 20}),
            (STRATEGY_GRID, 'fixed', {'upper_price': 120, 'lower_price': 80, 'grid_num': 5})
        ]
        
        for strategy_type, subtype, params in strategies:
            strategy = StrategyFactory.create_strategy(
                strategy_type=strategy_type,
                subtype=subtype,
                **params
            )
            
            # 验证策略实例
            self.assertIsNotNone(strategy)
            
            if strategy_type == STRATEGY_MACD_CROSS:
                self.assertIsInstance(strategy, MACDCrossStrategy)
            elif strategy_type == STRATEGY_MA_CROSS:
                self.assertIsInstance(strategy, MACrossStrategy)
            elif strategy_type == STRATEGY_RSI_OVERBOUGHT:
                self.assertIsInstance(strategy, RSIOverboughtStrategy)
            elif strategy_type == STRATEGY_BREAKOUT and subtype == 'bollinger':
                self.assertIsInstance(strategy, BollingerBreakoutStrategy)
            elif strategy_type == STRATEGY_GRID and subtype == 'fixed':
                self.assertIsInstance(strategy, GridStrategy)


if __name__ == '__main__':
    unittest.main()