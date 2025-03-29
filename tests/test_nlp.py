"""
测试自然语言处理模块
"""
import os
import sys
import unittest
import json

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.nlp.intent_parser import IntentParser
from config.constants import (
    CMD_ANALYZE, CMD_SCREEN, CMD_TRADE, CMD_BACKTEST, CMD_MONITOR,
    MARKET_TYPE_A_SHARE, MARKET_TYPE_US, MARKET_TYPE_HK, MARKET_TYPE_CRYPTO,
    TIMEFRAME_1D, INDICATOR_MA, INDICATOR_MACD
)


class TestIntentParser(unittest.TestCase):
    """测试意图解析器"""
    
    def setUp(self):
        """设置测试环境"""
        # 获取配置路径
        config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
        self.config_path = os.path.join(config_dir, "config.json")
        
        # 创建意图解析器
        self.parser = IntentParser(self.config_path)
    
    def test_analyze_intent(self):
        """测试分析意图解析"""
        query = "分析阿里巴巴近30天的走势"
        result = self.parser.parse(query)
        
        self.assertEqual(result['command_type'], CMD_ANALYZE)
        self.assertIn('BABA', result['symbols']) 
        
        query = "帮我看一下腾讯的MACD指标"
        result = self.parser.parse(query)
        
        self.assertEqual(result['command_type'], CMD_ANALYZE)
        self.assertIn('00700', result['symbols']) 
        self.assertIn(INDICATOR_MACD, result['indicators'])
    
    def test_screen_intent(self):
        """测试筛选意图解析"""
        query = "筛选出最近MACD金叉的A股股票"
        result = self.parser.parse(query)
        
        self.assertEqual(result['command_type'], CMD_SCREEN)
        self.assertEqual(result['market'], MARKET_TYPE_A_SHARE)
        self.assertIn(INDICATOR_MACD, result['indicators'])
    
    def test_trade_intent(self):
        """测试交易意图解析"""
        query = "买入10000元比特币"
        result = self.parser.parse(query)
        
        self.assertEqual(result['command_type'], CMD_TRADE)
        self.assertIn('BTC', result['symbols'])
        self.assertEqual(result['parameters'].get('amount'), 10000)
        
        query = "卖出所有腾讯股票"
        result = self.parser.parse(query)
        
        self.assertEqual(result['command_type'], CMD_TRADE)
        self.assertIn('00700', result['symbols'])
    
    def test_backtest_intent(self):
        """测试回测意图解析"""
        query = "回测茅台股票的均线交叉策略"
        result = self.parser.parse(query)
        
        self.assertEqual(result['command_type'], CMD_BACKTEST)
        self.assertIn('600519', result['symbols'])
        self.assertIn('ma_cross', result['strategies'])


if __name__ == '__main__':
    unittest.main()