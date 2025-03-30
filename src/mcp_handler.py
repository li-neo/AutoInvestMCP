"""
MCP处理器，负责处理用户自然语言请求并调用相应的功能模块
"""
import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple

from src.nlp.intent_parser import IntentParser
from src.data_api.api_factory import APIFactory
from src.indicators.indicator_factory import IndicatorFactory
from src.strategy.strategy_factory import StrategyFactory
from src.trade.trade_executor import TradeExecutor
from src.trade.trade_decision import TradeDecision
from config.constants import (
    CMD_ANALYZE, CMD_SCREEN, CMD_TRADE, CMD_BACKTEST, CMD_MONITOR
)


class MCPHandler:
    """MCP处理器，处理自然语言请求并调用相应功能"""
    
    def __init__(self, config_path: str):
        """初始化MCP处理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        
        # 初始化组件
        self.intent_parser = IntentParser(config_path)
        self.api_factory = APIFactory(config_path)
        self.trade_executor = TradeExecutor(self.api_factory)
        self.trade_decision = TradeDecision(self.api_factory, self.trade_executor)
        
        logging.info("MCP处理器初始化完成")
    
    def process_request(self, user_input: str) -> Dict[str, Any]:
        """处理用户请求
        
        Args:
            user_input: 用户输入的自然语言文本
            
        Returns:
            Dict: 处理结果
        """
        logging.info(f"接收到用户请求: {user_input}")
        
        try:
            # 解析用户意图
            parsed_intent = self.intent_parser.parse(user_input)
            logging.info(f"解析结果: {parsed_intent}")
            
            # 根据命令类型调用相应处理方法
            command_type = parsed_intent.get('command_type', '')
            
            if command_type == CMD_ANALYZE:
                result = self._handle_analyze(parsed_intent)
            elif command_type == CMD_SCREEN:
                result = self._handle_screen(parsed_intent)
            elif command_type == CMD_TRADE:
                result = self._handle_trade(parsed_intent)
            elif command_type == CMD_BACKTEST:
                result = self._handle_backtest(parsed_intent)
            elif command_type == CMD_MONITOR:
                result = self._handle_monitor(parsed_intent)
            else:
                result = {
                    'success': False,
                    'message': f"不支持的命令类型: {command_type}",
                    'data': None
                }

            result = {
                'success': True,
                'message': "处理完成",
                'data': parsed_intent
            }
            
            return result
        
        except Exception as e:
            logging.error(f"处理请求出错: {e}")
            return {
                'success': False,
                'message': f"处理请求出错: {str(e)}",
                'data': None
            }
    
    def _handle_analyze(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """处理分析请求
        
        Args:
            intent: 解析后的意图
            
        Returns:
            Dict: 处理结果
        """
        symbols = intent.get('symbols', [])
        market = intent.get('market', '')
        timeframe = intent.get('timeframe', '1d')
        indicators = intent.get('indicators', [])
        
        # 如果没有指定股票但指定了市场，获取该市场的热门股票
        if not symbols and market:
            try:
                api = self.api_factory.get_api('futu', market)
                if api:
                    # 简化实现，获取前10个股票
                    symbol_list = api.get_symbols(market)[:10]
                    symbols = symbol_list
            except Exception as e:
                logging.error(f"获取市场股票列表失败: {e}")
        
        # 如果没有有效的股票代码，返回错误
        if not symbols:
            return {
                'success': False,
                'message': "未指定股票代码或无法获取市场股票列表",
                'data': None
            }
        
        # 获取股票数据并添加指标
        results = {}
        
        for symbol in symbols:
            try:
                # 获取API
                api = self.api_factory.get_api_for_symbol(symbol)
                if not api:
                    results[symbol] = {
                        'success': False,
                        'message': f"找不到适合{symbol}的API"
                    }
                    continue
                
                # 获取市场数据
                market_data = api.get_market_data(symbol, timeframe, 100)
                if market_data.empty:
                    results[symbol] = {
                        'success': False,
                        'message': f"获取{symbol}市场数据失败"
                    }
                    continue
                
                # 获取股票基本信息
                ticker_info = api.get_ticker_info(symbol)
                
                # 计算技术指标
                indicator_configs = []
                for ind in indicators:
                    indicator_configs.append({
                        'type': ind,
                        'params': {}  # 使用默认参数
                    })
                
                if indicator_configs:
                    market_data = IndicatorFactory.calculate_indicators(market_data, indicator_configs)
                
                # 生成分析结果
                symbol_result = {
                    'success': True,
                    'ticker_info': ticker_info,
                    'latest_price': float(market_data['close'].iloc[-1]) if not market_data.empty else None,
                    'price_change': float(market_data['close'].iloc[-1] - market_data['close'].iloc[-2]) if len(market_data) > 1 else None,
                    'price_change_percent': float((market_data['close'].iloc[-1] / market_data['close'].iloc[-2] - 1) * 100) if len(market_data) > 1 else None,
                    'volume': float(market_data['volume'].iloc[-1]) if not market_data.empty else None,
                    'indicators': {}
                }
                
                # 添加指标信息
                for ind in indicators:
                    ind_columns = [col for col in market_data.columns if col.startswith(ind)]
                    if ind_columns:
                        symbol_result['indicators'][ind] = {
                            col: float(market_data[col].iloc[-1]) for col in ind_columns
                        }
                
                results[symbol] = symbol_result
                
            except Exception as e:
                logging.error(f"分析{symbol}出错: {e}")
                results[symbol] = {
                    'success': False,
                    'message': f"分析出错: {str(e)}"
                }
        
        return {
            'success': True,
            'message': "分析完成",
            'data': results
        }
    
    def _handle_screen(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """处理筛选请求
        
        Args:
            intent: 解析后的意图
            
        Returns:
            Dict: 处理结果
        """
        market = intent.get('market', '')
        indicators = intent.get('indicators', [])
        strategies = intent.get('strategies', [])
        parameters = intent.get('parameters', {})
        timeframe = intent.get('timeframe', '1d')
        
        # 确保指定了市场
        if not market:
            return {
                'success': False,
                'message': "未指定市场",
                'data': None
            }
        
        try:
            # 获取市场API
            api = self.api_factory.get_api('futu', market)
            if not api:
                return {
                    'success': False,
                    'message': f"找不到适合{market}市场的API",
                    'data': None
                }
            
            # 获取市场股票列表
            symbol_list = api.get_symbols(market)
            
            # 如果股票太多，限制数量以提高性能
            max_symbols = 50
            if len(symbol_list) > max_symbols:
                symbol_list = symbol_list[:max_symbols]
            
            # 对每个股票进行筛选
            screened_symbols = []
            
            for symbol in symbol_list:
                try:
                    # 获取市场数据
                    market_data = api.get_market_data(symbol, timeframe, 100)
                    if market_data.empty:
                        continue
                    
                    # 应用技术指标
                    indicator_configs = []
                    for ind in indicators:
                        indicator_configs.append({
                            'type': ind,
                            'params': {}  # 使用默认参数
                        })
                    
                    if indicator_configs:
                        market_data = IndicatorFactory.calculate_indicators(market_data, indicator_configs)
                    
                    # 应用策略
                    match_strategy = False
                    for strategy_name in strategies:
                        try:
                            # 创建策略实例
                            strategy = StrategyFactory.create_strategy(strategy_name)
                            
                            # 准备数据
                            data_with_signals = strategy.prepare_data(market_data)
                            data_with_signals = strategy.generate_signals(data_with_signals)
                            
                            # 检查最新信号
                            latest_signal = data_with_signals['signal'].iloc[-1]
                            if latest_signal == 1:  # 买入信号
                                match_strategy = True
                                break
                        except Exception as e:
                            logging.error(f"应用策略{strategy_name}到{symbol}出错: {e}")
                    
                    # 如果符合策略条件，添加到结果
                    if match_strategy:
                        ticker_info = api.get_ticker_info(symbol)
                        screened_symbols.append({
                            'symbol': symbol,
                            'name': ticker_info.get('name', ''),
                            'latest_price': float(market_data['close'].iloc[-1]),
                            'price_change_percent': float((market_data['close'].iloc[-1] / market_data['close'].iloc[-2] - 1) * 100) if len(market_data) > 1 else None,
                            'volume': float(market_data['volume'].iloc[-1]),
                            'matched_strategy': strategies[0] if strategies else None
                        })
                
                except Exception as e:
                    logging.error(f"筛选{symbol}出错: {e}")
            
            return {
                'success': True,
                'message': f"找到{len(screened_symbols)}个符合条件的股票",
                'data': {
                    'screened_symbols': screened_symbols,
                    'market': market,
                    'strategies': strategies,
                    'indicators': indicators
                }
            }
        
        except Exception as e:
            logging.error(f"筛选请求处理出错: {e}")
            return {
                'success': False,
                'message': f"筛选请求处理出错: {str(e)}",
                'data': None
            }
    
    def _handle_trade(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """处理交易请求
        
        Args:
            intent: 解析后的意图
            
        Returns:
            Dict: 处理结果
        """
        symbols = intent.get('symbols', [])
        strategies = intent.get('strategies', [])
        parameters = intent.get('parameters', {})
        
        # 如果没有指定股票，返回错误
        if not symbols:
            return {
                'success': False,
                'message': "未指定交易标的",
                'data': None
            }
        
        try:
            # 解析交易参数
            amount = parameters.get('amount', 1000.0)  # 默认交易金额
            
            # 对每个股票执行交易决策
            trade_results = []
            
            for symbol in symbols:
                # 对于有策略的情况，使用策略生成交易决策
                if strategies:
                    strategy_name = strategies[0]
                    strategy_config = {
                        'strategy_type': strategy_name,
                        'strategy_params': {}  # 使用默认参数
                    }
                    
                    # 生成决策
                    decisions = self.trade_decision.make_decision(strategy_config, [symbol])
                    
                    # 执行决策
                    if decisions:
                        execution_results = self.trade_decision.execute_decisions(decisions)
                        trade_results.append({
                            'symbol': symbol,
                            'strategy': strategy_name,
                            'decisions': decisions,
                            'execution_results': execution_results
                        })
                
                # 对于没有策略的情况，直接执行买入操作
                else:
                    # 获取最新价格
                    api = self.api_factory.get_api_for_symbol(symbol)
                    if not api:
                        trade_results.append({
                            'symbol': symbol,
                            'success': False,
                            'message': f"找不到适合{symbol}的API"
                        })
                        continue
                    
                    ticker_info = api.get_ticker_info(symbol)
                    current_price = ticker_info.get('price', 0.0)
                    
                    if current_price <= 0:
                        trade_results.append({
                            'symbol': symbol,
                            'success': False,
                            'message': f"获取{symbol}价格失败"
                        })
                        continue
                    
                    # 计算交易数量
                    trade_amount = amount / current_price
                    
                    # 执行交易
                    order_result = self.trade_executor.place_order(
                        symbol=symbol,
                        order_type='MARKET',
                        side='BUY',
                        amount=trade_amount
                    )
                    
                    trade_results.append({
                        'symbol': symbol,
                        'success': 'error' not in order_result,
                        'message': order_result.get('error', '交易成功'),
                        'order_result': order_result
                    })
            
            return {
                'success': True,
                'message': "交易请求处理完成",
                'data': {
                    'trade_results': trade_results
                }
            }
        
        except Exception as e:
            logging.error(f"交易请求处理出错: {e}")
            return {
                'success': False,
                'message': f"交易请求处理出错: {str(e)}",
                'data': None
            }
    
    def _handle_backtest(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """处理回测请求
        
        Args:
            intent: 解析后的意图
            
        Returns:
            Dict: 处理结果
        """
        symbols = intent.get('symbols', [])
        strategies = intent.get('strategies', [])
        parameters = intent.get('parameters', {})
        timeframe = intent.get('timeframe', '1d')
        
        # 如果没有指定股票和策略，返回错误
        if not symbols or not strategies:
            return {
                'success': False,
                'message': "未指定交易标的或策略",
                'data': None
            }
        
        try:
            # 解析回测参数
            days = parameters.get('days', 365)  # 默认回测一年
            initial_capital = parameters.get('amount', 10000.0)  # 初始资金
            
            # 对每个股票执行回测
            backtest_results = []
            
            for symbol in symbols:
                for strategy_name in strategies:
                    # 创建策略配置
                    strategy_config = {
                        'strategy_type': strategy_name,
                        'strategy_params': {}  # 使用默认参数
                    }
                    
                    # 执行回测
                    result = self.trade_decision.backtest_strategy(
                        strategy_config=strategy_config,
                        symbol=symbol,
                        timeframe=timeframe,
                        initial_capital=initial_capital
                    )
                    
                    backtest_results.append({
                        'symbol': symbol,
                        'strategy': strategy_name,
                        'success': 'error' not in result,
                        'message': result.get('error', '回测成功'),
                        'result': result
                    })
            
            return {
                'success': True,
                'message': "回测完成",
                'data': {
                    'backtest_results': backtest_results
                }
            }
        
        except Exception as e:
            logging.error(f"回测请求处理出错: {e}")
            return {
                'success': False,
                'message': f"回测请求处理出错: {str(e)}",
                'data': None
            }
    
    def _handle_monitor(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """处理监控请求
        
        Args:
            intent: 解析后的意图
            
        Returns:
            Dict: 处理结果
        """
        # 监控功能需要服务器持续运行，这里只返回一个说明
        return {
            'success': True,
            'message': "监控功能需要在服务器端实现，暂不支持在MCP接口中直接使用",
            'data': {
                'request': intent
            }
        }