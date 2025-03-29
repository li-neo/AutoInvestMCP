"""
测试技术指标模块
"""
import os
import sys
import unittest
import pandas as pd
import numpy as np

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.indicators.indicator_factory import IndicatorFactory
from src.indicators.moving_averages import SimpleMovingAverage, ExponentialMovingAverage, MACD, BollingerBands
from src.indicators.oscillators import RSI, KDJ, VolumeProfile
from config.constants import (
    INDICATOR_MA, INDICATOR_EMA, INDICATOR_MACD, INDICATOR_RSI,
    INDICATOR_BOLLINGER, INDICATOR_KDJ, INDICATOR_VOLUME
)


class TestIndicators(unittest.TestCase):
    """测试技术指标"""
    
    def setUp(self):
        """设置测试环境"""
        # 创建模拟的OHLCV数据
        np.random.seed(42)
        
        # 创建100条记录的模拟数据
        n = 100
        dates = pd.date_range('2023-01-01', periods=n)
        
        # 生成随机价格数据
        close = 100 + np.cumsum(np.random.normal(0, 1, n))
        open_prices = close - np.random.normal(0, 1, n)
        high = np.maximum(close, open_prices) + np.random.normal(0, 0.5, n)
        low = np.minimum(close, open_prices) - np.random.normal(0, 0.5, n)
        volume = np.random.normal(1000000, 500000, n)
        volume = np.abs(volume)
        
        # 创建DataFrame
        self.data = pd.DataFrame({
            'open': open_prices,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        }, index=dates)
    
    def test_simple_moving_average(self):
        """测试简单移动平均线"""
        # 创建SMA实例
        sma = SimpleMovingAverage(window=20)
        
        # 计算SMA
        result = sma.calculate(self.data)
        
        # 验证结果
        self.assertIn('ma_20', result.columns)
        self.assertEqual(len(result), len(self.data))
        
        # 前19个值应该是NaN
        self.assertTrue(np.isnan(result['ma_20'].iloc[18]))
        
        # 第20个值应该是前20个close的平均
        expected_ma = self.data['close'].iloc[:20].mean()
        self.assertAlmostEqual(result['ma_20'].iloc[19], expected_ma)
    
    def test_exponential_moving_average(self):
        """测试指数移动平均线"""
        # 创建EMA实例
        ema = ExponentialMovingAverage(window=20)
        
        # 计算EMA
        result = ema.calculate(self.data)
        
        # 验证结果
        self.assertIn('ema_20', result.columns)
        self.assertEqual(len(result), len(self.data))
    
    def test_macd(self):
        """测试MACD"""
        # 创建MACD实例
        macd = MACD(fast_period=12, slow_period=26, signal_period=9)
        
        # 计算MACD
        result = macd.calculate(self.data)
        
        # 验证结果
        for col in ['macd', 'macd_signal', 'macd_hist']:
            self.assertIn(col, result.columns)
        
        # 生成信号
        result = macd.get_signal(result, signal_type='cross')
        self.assertIn('macd_cross_signal', result.columns)
    
    def test_rsi(self):
        """测试RSI"""
        # 创建RSI实例
        rsi = RSI(window=14)
        
        # 计算RSI
        result = rsi.calculate(self.data)
        
        # 验证结果
        self.assertIn('rsi_14', result.columns)
        
        # RSI值应该在0-100之间
        valid_rsi = result['rsi_14'].dropna()
        self.assertTrue((valid_rsi >= 0).all() and (valid_rsi <= 100).all())
    
    def test_bollinger_bands(self):
        """测试布林带"""
        # 创建布林带实例
        bollinger = BollingerBands(window=20, std_dev=2.0)
        
        # 计算布林带
        result = bollinger.calculate(self.data)
        
        # 验证结果
        for col in ['bollinger_ma', 'bollinger_upper', 'bollinger_lower']:
            self.assertIn(col, result.columns)
        
        # 验证上轨、下轨和中轨的关系
        valid_data = result.dropna()
        self.assertTrue((valid_data['bollinger_upper'] > valid_data['bollinger_ma']).all())
        self.assertTrue((valid_data['bollinger_ma'] > valid_data['bollinger_lower']).all())
    
    def test_indicator_factory(self):
        """测试指标工厂"""
        # 测试创建不同类型的指标
        indicators = [
            {'type': INDICATOR_MA, 'params': {'window': 10}},
            {'type': INDICATOR_EMA, 'params': {'window': 20}},
            {'type': INDICATOR_MACD, 'params': {}},
            {'type': INDICATOR_RSI, 'params': {'window': 14}},
            {'type': INDICATOR_BOLLINGER, 'params': {'window': 20}}
        ]
        
        # 计算多个指标
        result = IndicatorFactory.calculate_indicators(self.data, indicators)
        
        # 验证结果
        self.assertIn('ma_10', result.columns)
        self.assertIn('ema_20', result.columns)
        self.assertIn('macd', result.columns)
        self.assertIn('rsi_14', result.columns)
        self.assertIn('bollinger_upper', result.columns)


if __name__ == '__main__':
    unittest.main()