"""
交易决策引擎，负责根据策略信号和风险管理生成交易指令
"""
import time
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np

from src.data_api.api_factory import APIFactory
from src.strategy.strategy_factory import StrategyFactory
from src.trade.trade_executor import TradeExecutor


class TradeDecision:
    """交易决策引擎"""
    
    def __init__(self, api_factory: APIFactory, trade_executor: TradeExecutor):
        """初始化交易决策引擎
        
        Args:
            api_factory: API工厂实例
            trade_executor: 交易执行器实例
        """
        self.api_factory = api_factory
        self.trade_executor = trade_executor
        self.risk_params = {
            'max_position_size': 0.1,  # 单个头寸最大仓位比例
            'max_drawdown': 0.1,      # 最大允许回撤
            'stop_loss_pct': 0.05,     # 止损百分比
            'take_profit_pct': 0.1,    # 止盈百分比
        }
    
    def _fetch_market_data(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """获取市场数据
        
        Args:
            symbol: 交易对/股票代码
            timeframe: 时间周期
            limit: 获取的K线数量
            
        Returns:
            pd.DataFrame: 市场数据
        """
        # 获取适合该交易对/股票的API
        api = self.api_factory.get_api_for_symbol(symbol)
        if not api:
            logging.error(f"找不到适合{symbol}的API")
            return pd.DataFrame()
        
        try:
            # 获取K线数据
            market_data = api.get_market_data(symbol, timeframe, limit)
            return market_data
        except Exception as e:
            logging.error(f"获取市场数据失败: {e}")
            return pd.DataFrame()
    
    def _apply_risk_management(self, signal: int, symbol: str, 
                              current_price: float, account_info: Dict[str, Any]) -> Tuple[bool, float]:
        """应用风险管理规则
        
        Args:
            signal: 策略信号(1:买入, -1:卖出, 0:不操作)
            symbol: 交易对/股票代码
            current_price: 当前价格
            account_info: 账户信息
            
        Returns:
            Tuple[bool, float]: (是否执行交易, 交易数量)
        """
        # 如果没有信号，不执行交易
        if signal == 0:
            return False, 0.0
        
        # 获取总资产
        total_assets = 0.0
        for api_name, info in account_info.items():
            if isinstance(info, dict) and 'error' not in info:
                total_assets += info.get('total_assets', 0.0)
        
        if total_assets <= 0:
            logging.error("账户总资产为0，无法执行交易")
            return False, 0.0
        
        # 获取当前持仓
        current_position = self.trade_executor.positions.get(symbol, 0.0)
        position_value = current_position * current_price
        
        # 计算可用资金
        available_capital = total_assets * self.risk_params['max_position_size']
        
        if signal == 1:  # 买入信号
            # 如果已有持仓，检查是否超过最大仓位
            if position_value >= available_capital:
                logging.info(f"{symbol}持仓已达最大仓位，不再买入")
                return False, 0.0
            
            # 计算可买入的数量
            remaining_capital = available_capital - position_value
            buy_amount = remaining_capital / current_price
            
            # 如果数量太小，不执行交易
            if buy_amount * current_price < 10:  # 假设最小交易金额为10
                logging.info(f"{symbol}买入数量太小，不执行交易")
                return False, 0.0
            
            return True, buy_amount
            
        elif signal == -1:  # 卖出信号
            # 如果没有持仓，不执行卖出
            if current_position <= 0:
                logging.info(f"没有{symbol}持仓，不执行卖出")
                return False, 0.0
            
            # 全部卖出
            return True, current_position
    
    def make_decision(self, strategy_config: Dict[str, Any], symbols: List[str]) -> List[Dict[str, Any]]:
        """根据策略和风险管理生成交易决策
        
        Args:
            strategy_config: 策略配置
            symbols: 要交易的交易对/股票列表
            
        Returns:
            List[Dict]: 交易决策列表
        """
        decisions = []
        
        # 解析策略配置
        strategy_type = strategy_config.get('strategy_type')
        strategy_subtype = strategy_config.get('strategy_subtype')
        strategy_params = strategy_config.get('strategy_params', {})
        timeframe = strategy_config.get('timeframe', '1d')
        data_limit = strategy_config.get('data_limit', 100)
        
        # 创建策略实例
        try:
            strategy = StrategyFactory.create_strategy(
                strategy_type=strategy_type,
                subtype=strategy_subtype,
                **strategy_params
            )
        except Exception as e:
            logging.error(f"创建策略失败: {e}")
            return []
        
        # 获取账户信息
        account_info = self.trade_executor.get_account_info()
        
        # 对每个交易对/股票生成决策
        for symbol in symbols:
            try:
                # 获取市场数据
                market_data = self._fetch_market_data(symbol, timeframe, data_limit)
                if market_data.empty:
                    logging.error(f"获取{symbol}市场数据失败")
                    continue
                
                # 添加指标和信号
                data_with_signals = strategy.prepare_data(market_data)
                data_with_signals = strategy.generate_signals(data_with_signals)
                
                # 获取最新的信号
                latest_signal = data_with_signals['signal'].iloc[-1]
                current_price = data_with_signals['close'].iloc[-1]
                
                # 应用风险管理
                execute_trade, trade_amount = self._apply_risk_management(
                    latest_signal, symbol, current_price, account_info
                )
                
                # 生成交易决策
                decision = {
                    'symbol': symbol,
                    'strategy': f"{strategy_type}/{strategy_subtype}" if strategy_subtype else strategy_type,
                    'signal': latest_signal,
                    'current_price': current_price,
                    'execute_trade': execute_trade,
                    'trade_amount': trade_amount,
                    'side': 'BUY' if latest_signal == 1 else 'SELL' if latest_signal == -1 else 'HOLD',
                    'timestamp': time.time()
                }
                
                decisions.append(decision)
                
            except Exception as e:
                logging.error(f"为{symbol}生成交易决策失败: {e}")
        
        return decisions
    
    def execute_decisions(self, decisions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """执行交易决策
        
        Args:
            decisions: 交易决策列表
            
        Returns:
            List[Dict]: 执行结果列表
        """
        orders = []
        
        # 将决策转化为订单
        for decision in decisions:
            if decision.get('execute_trade', False):
                order = {
                    'symbol': decision.get('symbol'),
                    'side': decision.get('side'),
                    'order_type': 'MARKET',
                    'amount': decision.get('trade_amount', 0.0),
                    'price': None  # 市价单
                }
                
                orders.append(order)
        
        # 执行订单
        results = self.trade_executor.execute_order_list(orders)
        
        return results
    
    def set_risk_params(self, risk_params: Dict[str, float]):
        """设置风险管理参数
        
        Args:
            risk_params: 风险管理参数字典
        """
        self.risk_params.update(risk_params)
    
    def backtest_strategy(self, strategy_config: Dict[str, Any], 
                        symbol: str, timeframe: str, 
                        start_date: str = None, end_date: str = None,
                        initial_capital: float = 10000.0) -> Dict[str, Any]:
        """回测策略
        
        Args:
            strategy_config: 策略配置
            symbol: 交易对/股票代码
            timeframe: 时间周期
            start_date: 起始日期，格式为"YYYY-MM-DD"
            end_date: 结束日期，格式为"YYYY-MM-DD"
            initial_capital: 初始资金
            
        Returns:
            Dict: 回测结果
        """
        # 解析策略配置
        strategy_type = strategy_config.get('strategy_type')
        strategy_subtype = strategy_config.get('strategy_subtype')
        strategy_params = strategy_config.get('strategy_params', {})
        
        # 创建策略实例
        try:
            strategy = StrategyFactory.create_strategy(
                strategy_type=strategy_type,
                subtype=strategy_subtype,
                **strategy_params
            )
        except Exception as e:
            logging.error(f"创建策略失败: {e}")
            return {'error': str(e)}
        
        # 获取市场数据
        api = self.api_factory.get_api_for_symbol(symbol)
        if not api:
            error_msg = f"找不到适合{symbol}的API"
            logging.error(error_msg)
            return {'error': error_msg}
        
        try:
            # 获取足够的历史数据
            # 注意：这里简化了实现，实际可能需要分批获取和合并数据
            market_data = api.get_market_data(symbol, timeframe, 1000)
            
            # 过滤日期范围
            if start_date:
                market_data = market_data[market_data.index >= start_date]
            if end_date:
                market_data = market_data[market_data.index <= end_date]
            
            # 执行回测
            backtest_result = strategy.backtest(market_data, initial_capital)
            
            return backtest_result
        except Exception as e:
            error_msg = f"回测失败: {e}"
            logging.error(error_msg)
            return {'error': error_msg}