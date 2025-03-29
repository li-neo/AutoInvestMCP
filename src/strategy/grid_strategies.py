"""
网格交易策略实现
"""
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np

from src.strategy.strategy_base import StrategyBase
from config.constants import STRATEGY_GRID


class GridStrategy(StrategyBase):
    """等距网格交易策略"""
    
    def __init__(self, upper_price: float, lower_price: float, grid_num: int,
                 price_key: str = 'close'):
        """初始化等距网格交易策略
        
        Args:
            upper_price: 网格上边界价格
            lower_price: 网格下边界价格
            grid_num: 网格数量
            price_key: 使用的价格列名
        """
        super().__init__(STRATEGY_GRID)
        
        # 验证参数
        if upper_price <= lower_price:
            raise ValueError("上边界价格必须大于下边界价格")
        if grid_num <= 0:
            raise ValueError("网格数量必须大于0")
        
        # 设置策略参数
        self.params = {
            'upper_price': upper_price,
            'lower_price': lower_price,
            'grid_num': grid_num,
            'price_key': price_key
        }
        
        # 计算网格价格
        self.grid_prices = self._calculate_grid_prices()
    
    def _calculate_grid_prices(self) -> List[float]:
        """计算网格价格
        
        Returns:
            List[float]: 网格价格列表，从低到高排序
        """
        upper = self.params['upper_price']
        lower = self.params['lower_price']
        num = self.params['grid_num']
        
        # 计算每个网格的价格间隔
        interval = (upper - lower) / num
        
        # 生成所有网格价格
        prices = [lower + i * interval for i in range(num + 1)]
        
        return prices
    
    def prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """准备数据，添加网格价格列
        
        Args:
            data: 原始数据DataFrame
            
        Returns:
            pd.DataFrame: 添加了网格相关列的DataFrame
        """
        data = data.copy()
        price_key = self.params['price_key']
        
        # 添加当前价格所在的网格区间
        data['grid_position'] = 0
        
        for i in range(len(self.grid_prices) - 1):
            lower = self.grid_prices[i]
            upper = self.grid_prices[i + 1]
            data.loc[(data[price_key] >= lower) & (data[price_key] < upper), 'grid_position'] = i
        
        # 处理边界情况
        data.loc[data[price_key] >= self.grid_prices[-1], 'grid_position'] = len(self.grid_prices) - 2
        
        return data
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成网格交易信号
        
        Args:
            data: 包含网格位置的DataFrame
            
        Returns:
            pd.DataFrame: 添加了策略信号的DataFrame
        """
        data = data.copy()
        
        # 确保包含网格位置
        if 'grid_position' not in data.columns:
            data = self.prepare_data(data)
        
        # 初始化信号列
        data['signal'] = 0
        
        # 计算网格位置变化
        data['grid_position_change'] = data['grid_position'].diff()
        
        # 根据网格位置变化生成信号
        # 向上穿越网格：卖出 (价格上涨，卖出获利)
        data.loc[data['grid_position_change'] > 0, 'signal'] = -1
        
        # 向下穿越网格：买入 (价格下跌，买入)
        data.loc[data['grid_position_change'] < 0, 'signal'] = 1
        
        return data
    
    def backtest(self, data: pd.DataFrame, initial_capital: float = 10000.0,
                 shares_per_grid: float = 1.0, commission: float = 0.0) -> Dict[str, Any]:
        """回测网格交易策略
        
        Args:
            data: 价格数据
            initial_capital: 初始资金
            shares_per_grid: 每个网格交易的股数/数量
            commission: 手续费比例
            
        Returns:
            Dict: 回测结果
        """
        # 准备数据并生成信号
        data = self.prepare_data(data.copy())
        data = self.generate_signals(data)
        
        # 初始化回测变量
        capital = initial_capital
        positions = {}  # 记录每个网格的持仓
        trades = []
        
        # 添加回测列
        data['capital'] = 0.0
        data['position_value'] = 0.0
        data['equity'] = 0.0
        
        # 遍历每个交易日
        for i in range(1, len(data)):
            price = data['close'].iloc[i]
            grid_position = data['grid_position'].iloc[i]
            signal = data['signal'].iloc[i]
            
            # 处理买入信号
            if signal == 1:
                # 执行网格买入
                cost = shares_per_grid * price * (1 + commission)
                
                if cost <= capital:
                    capital -= cost
                    
                    # 更新该网格的持仓
                    if grid_position in positions:
                        positions[grid_position] += shares_per_grid
                    else:
                        positions[grid_position] = shares_per_grid
                    
                    trades.append({
                        'type': 'buy',
                        'date': data.index[i],
                        'price': price,
                        'shares': shares_per_grid,
                        'grid': grid_position,
                        'cost': cost,
                        'capital': capital
                    })
            
            # 处理卖出信号
            elif signal == -1:
                # 寻找最低网格的持仓进行卖出
                for pos in sorted(positions.keys()):
                    if positions[pos] > 0:
                        # 执行网格卖出
                        proceeds = positions[pos] * price * (1 - commission)
                        original_cost = positions[pos] * data['close'].iloc[positions[pos] == grid_position].iloc[0] * (1 + commission)
                        profit = proceeds - original_cost
                        
                        capital += proceeds
                        positions[pos] = 0  # 清空该网格持仓
                        
                        trades.append({
                            'type': 'sell',
                            'date': data.index[i],
                            'price': price,
                            'shares': positions[pos],
                            'grid': pos,
                            'proceeds': proceeds,
                            'profit': profit,
                            'capital': capital
                        })
                        break
            
            # 更新每日数据
            total_position_value = sum(pos * price for pos in positions.values())
            data['capital'].iloc[i] = capital
            data['position_value'].iloc[i] = total_position_value
            data['equity'].iloc[i] = capital + total_position_value
        
        # 计算回测结果
        final_equity = data['equity'].iloc[-1]
        
        # 计算策略收益
        total_return = (final_equity / initial_capital - 1) * 100
        annual_return = total_return / (len(data) / 252)  # 假设每年有252个交易日
        
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
            'max_drawdown_pct': max_drawdown,
            'total_trades': len(trades),
            'trades': trades,
            'equity_curve': data[['equity']]
        }
        
        return result
    
    def get_description(self) -> str:
        """获取策略的描述
        
        Returns:
            str: 策略描述
        """
        return f"等距网格交易策略(上边界={self.params['upper_price']}, 下边界={self.params['lower_price']}, 网格数量={self.params['grid_num']})"


class DynamicGridStrategy(GridStrategy):
    """动态网格交易策略，根据波动率自动调整网格"""
    
    def __init__(self, price: float, volatility_window: int = 20, grid_num: int = 10,
                 volatility_multiplier: float = 2.0, price_key: str = 'close'):
        """初始化动态网格交易策略
        
        Args:
            price: 当前价格，作为网格中心
            volatility_window: 计算波动率的窗口大小
            grid_num: 网格数量
            volatility_multiplier: 波动率乘数，用于确定网格范围
            price_key: 使用的价格列名
        """
        # 先使用临时值初始化父类
        super().__init__(price * 1.1, price * 0.9, grid_num, price_key)
        
        # 更新为动态网格参数
        self.params.update({
            'center_price': price,
            'volatility_window': volatility_window,
            'volatility_multiplier': volatility_multiplier
        })
    
    def prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """准备数据，计算波动率并动态调整网格
        
        Args:
            data: 原始数据DataFrame
            
        Returns:
            pd.DataFrame: 添加了网格相关列的DataFrame
        """
        data = data.copy()
        price_key = self.params['price_key']
        
        # 计算价格波动率（标准差）
        data['volatility'] = data[price_key].rolling(window=self.params['volatility_window']).std()
        
        # 动态调整网格范围
        center_price = self.params['center_price']
        volatility_multiplier = self.params['volatility_multiplier']
        grid_num = self.params['grid_num']
        
        # 使用最近的波动率来调整网格边界
        # 从第volatility_window行开始有波动率数据
        for i in range(self.params['volatility_window'], len(data)):
            volatility = data['volatility'].iloc[i]
            
            # 计算动态的上下边界
            upper_price = center_price + (volatility * volatility_multiplier)
            lower_price = center_price - (volatility * volatility_multiplier)
            
            # 更新网格价格
            self.params['upper_price'] = upper_price
            self.params['lower_price'] = lower_price
            self.grid_prices = self._calculate_grid_prices()
            
            # 计算当前价格所在网格
            price = data[price_key].iloc[i]
            grid_position = 0
            
            for j in range(len(self.grid_prices) - 1):
                if self.grid_prices[j] <= price < self.grid_prices[j + 1]:
                    grid_position = j
                    break
            
            data['grid_position'].iloc[i] = grid_position
        
        return data
    
    def get_description(self) -> str:
        """获取策略的描述
        
        Returns:
            str: 策略描述
        """
        return f"动态网格交易策略(中心价格={self.params['center_price']}, 波动率窗口={self.params['volatility_window']}, 波动率乘数={self.params['volatility_multiplier']}, 网格数量={self.params['grid_num']})"