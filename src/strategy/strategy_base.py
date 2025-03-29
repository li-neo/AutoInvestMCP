"""
策略基类，定义了所有交易策略的通用接口
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np

from src.indicators.indicator_factory import IndicatorFactory


class StrategyBase(ABC):
    """交易策略基类"""
    
    def __init__(self, name: str):
        """初始化策略
        
        Args:
            name: 策略名称
        """
        self.name = name
        self.indicators = []
        self.params = {}
        
    def add_indicator(self, indicator_type: str, params: Dict[str, Any], signal_params: Optional[Dict[str, Any]] = None):
        """添加技术指标到策略
        
        Args:
            indicator_type: 指标类型
            params: 指标参数
            signal_params: 信号参数
        """
        self.indicators.append({
            'type': indicator_type,
            'params': params,
            'signal_params': signal_params or {}
        })
    
    def prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """准备数据，计算所需的指标
        
        Args:
            data: 原始数据DataFrame
            
        Returns:
            pd.DataFrame: 添加了指标的DataFrame
        """
        # 使用指标工厂计算指标
        result = IndicatorFactory.calculate_indicators(data, self.indicators)
        
        # 计算信号
        result = IndicatorFactory.get_indicator_signals(result, self.indicators)
        
        return result
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """基于策略规则生成交易信号
        
        Args:
            data: 包含指标的DataFrame
            
        Returns:
            pd.DataFrame: 添加了策略信号的DataFrame
        """
        pass
    
    def backtest(self, data: pd.DataFrame, initial_capital: float = 10000.0, 
                 position_size: float = 1.0, commission: float = 0.0) -> Dict[str, Any]:
        """回测策略性能
        
        Args:
            data: 价格数据
            initial_capital: 初始资金
            position_size: 仓位大小比例(0.0-1.0)
            commission: 手续费比例
            
        Returns:
            Dict: 回测结果
        """
        # 准备数据并生成信号
        data = self.prepare_data(data.copy())
        data = self.generate_signals(data)
        
        # 初始化回测变量
        capital = initial_capital
        position = 0.0
        entry_price = 0.0
        trades = []
        
        # 添加回测列
        data['capital'] = 0.0
        data['position'] = 0.0
        data['equity'] = 0.0
        
        # 遍历每个交易日
        for i in range(1, len(data)):
            price = data['close'].iloc[i]
            signal = data['signal'].iloc[i-1]  # 使用前一个信号
            
            # 处理信号
            if signal == 1 and position == 0:  # 买入信号
                # 计算可买入的数量
                shares = (capital * position_size) / price
                cost = shares * price * (1 + commission)
                
                if cost <= capital:
                    position = shares
                    entry_price = price
                    capital -= cost
                    trades.append({
                        'type': 'buy',
                        'date': data.index[i],
                        'price': price,
                        'shares': shares,
                        'cost': cost,
                        'capital': capital
                    })
            
            elif signal == -1 and position > 0:  # 卖出信号
                # 计算卖出收益
                proceeds = position * price * (1 - commission)
                profit = proceeds - (position * entry_price * (1 + commission))
                
                capital += proceeds
                trades.append({
                    'type': 'sell',
                    'date': data.index[i],
                    'price': price,
                    'shares': position,
                    'proceeds': proceeds,
                    'profit': profit,
                    'profit_pct': profit / (position * entry_price) * 100,
                    'capital': capital
                })
                position = 0
                entry_price = 0
            
            # 更新每日数据
            data['capital'].iloc[i] = capital
            data['position'].iloc[i] = position
            data['equity'].iloc[i] = capital + (position * price)
        
        # 计算性能指标
        data['returns'] = data['equity'].pct_change()
        
        # 如果最后还有持仓，模拟平仓
        final_equity = data['equity'].iloc[-1]
        
        # 计算回测结果
        total_return = (final_equity / initial_capital - 1) * 100
        annual_return = total_return / (len(data) / 252)  # 假设每年有252个交易日
        
        # 计算夏普比率
        risk_free_rate = 0.02  # 假设无风险利率为2%
        sharpe_ratio = (annual_return / 100 - risk_free_rate) / (data['returns'].std() * np.sqrt(252))
        
        # 计算最大回撤
        equity_curve = data['equity']
        rolling_max = equity_curve.cummax()
        drawdown = (equity_curve - rolling_max) / rolling_max
        max_drawdown = drawdown.min() * 100
        
        # 汇总结果
        result = {
            'initial_capital': initial_capital,
            'final_equity': final_equity,
            'total_return_pct': total_return,
            'annual_return_pct': annual_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown_pct': max_drawdown,
            'total_trades': len(trades),
            'winning_trades': sum(1 for t in trades if t.get('type') == 'sell' and t.get('profit', 0) > 0),
            'losing_trades': sum(1 for t in trades if t.get('type') == 'sell' and t.get('profit', 0) <= 0),
            'trades': trades,
            'equity_curve': data[['equity']]
        }
        
        if len(trades) > 0:
            sell_trades = [t for t in trades if t.get('type') == 'sell']
            if sell_trades:
                result['avg_profit_pct'] = sum(t.get('profit_pct', 0) for t in sell_trades) / len(sell_trades)
                
                win_trades = [t for t in sell_trades if t.get('profit', 0) > 0]
                loss_trades = [t for t in sell_trades if t.get('profit', 0) <= 0]
                
                if win_trades:
                    result['avg_win_pct'] = sum(t.get('profit_pct', 0) for t in win_trades) / len(win_trades)
                
                if loss_trades:
                    result['avg_loss_pct'] = sum(t.get('profit_pct', 0) for t in loss_trades) / len(loss_trades)
                
                result['win_rate'] = len(win_trades) / len(sell_trades) if sell_trades else 0
        
        return result
    
    def set_params(self, **kwargs):
        """设置策略参数
        
        Args:
            **kwargs: 参数字典
        """
        self.params.update(kwargs)
    
    def get_description(self) -> str:
        """获取策略的描述
        
        Returns:
            str: 策略描述
        """
        return f"{self.name} 策略"