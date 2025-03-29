"""
测试MCP处理器模块
"""
import os
import sys
import unittest
import json
from unittest.mock import patch, MagicMock

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mcp_handler import MCPHandler
from config.constants import (
    CMD_ANALYZE, CMD_SCREEN, CMD_TRADE, CMD_BACKTEST, CMD_MONITOR
)


class TestMCPHandler(unittest.TestCase):
    """测试MCP处理器"""
    
    def setUp(self):
        """设置测试环境"""
        # 获取配置路径
        config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
        self.config_path = os.path.join(config_dir, "config.json")
    
    @patch('src.mcp_handler.IntentParser')
    @patch('src.mcp_handler.APIFactory')
    def test_process_analyze_request(self, mock_api_factory, mock_intent_parser):
        """测试处理分析请求"""
        # 模拟解析结果
        mock_parser = MagicMock()
        mock_parser.parse.return_value = {
            'command_type': CMD_ANALYZE,
            'symbols': ['AAPL'],
            'market': 'US',
            'timeframe': '1d',
            'indicators': ['macd', 'rsi'],
            'parameters': {}
        }
        mock_intent_parser.return_value = mock_parser
        
        # 模拟API返回数据
        mock_api = MagicMock()
        
        # 模拟获取市场数据和股票信息
        mock_api.get_market_data.return_value = MagicMock()
        mock_api.get_ticker_info.return_value = {
            'symbol': 'AAPL',
            'name': 'Apple Inc.',
            'price': 150.0,
            'volume': 1000000
        }
        mock_api_factory_instance = MagicMock()
        mock_api_factory_instance.get_api_for_symbol.return_value = mock_api
        mock_api_factory.return_value = mock_api_factory_instance
        
        # 创建MCP处理器
        handler = MCPHandler(self.config_path)
        
        # 处理请求
        result = handler.process_request("分析苹果公司股票")
        
        # 验证结果
        self.assertTrue(result['success'])
        self.assertIn('message', result)
        self.assertIn('data', result)
    
    @patch('src.mcp_handler.IntentParser')
    @patch('src.mcp_handler.APIFactory')
    def test_process_screen_request(self, mock_api_factory, mock_intent_parser):
        """测试处理筛选请求"""
        # 模拟解析结果
        mock_parser = MagicMock()
        mock_parser.parse.return_value = {
            'command_type': CMD_SCREEN,
            'symbols': [],
            'market': 'US',
            'timeframe': '1d',
            'indicators': ['macd'],
            'strategies': ['macd_cross'],
            'parameters': {}
        }
        mock_intent_parser.return_value = mock_parser
        
        # 模拟API返回数据
        mock_api = MagicMock()
        
        # 模拟获取股票列表
        mock_api.get_symbols.return_value = ['AAPL', 'MSFT', 'GOOGL']
        
        # 模拟获取市场数据和股票信息
        mock_api.get_market_data.return_value = MagicMock()
        mock_api.get_ticker_info.return_value = {
            'symbol': 'AAPL',
            'name': 'Apple Inc.',
            'price': 150.0,
            'volume': 1000000
        }
        mock_api_factory_instance = MagicMock()
        mock_api_factory_instance.get_api.return_value = mock_api
        mock_api_factory_instance.get_api_for_symbol.return_value = mock_api
        mock_api_factory.return_value = mock_api_factory_instance
        
        # 创建MCP处理器
        handler = MCPHandler(self.config_path)
        
        # 处理请求
        result = handler.process_request("筛选MACD金叉的美股")
        
        # 验证结果
        self.assertTrue(result['success'])
        self.assertIn('message', result)
        self.assertIn('data', result)


if __name__ == '__main__':
    unittest.main()