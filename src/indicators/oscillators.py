"""
振荡器指标实现，包括RSI、KDJ等
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List

from src.indicators.indicator_base import IndicatorBase


class RSI(IndicatorBase):
    """相对强弱指数(RSI)"""
    
    def __init__(self, window: int = 14, price_key: str = 'close'):
        """初始化RSI指标
        
        Args:
            window: 窗口大小
            price_key: 使用的价格列名，默认为收盘价
        """
        super().__init__('rsi')
        self.window = window
        self.price_key = price_key
        self.column_name = f"rsi_{window}"
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """计算RSI指标
        
        Args:
            data: 包含OHLCV数据的DataFrame
            **kwargs: 其他参数
            
        Returns:
            pd.DataFrame: 添加了RSI指标列的DataFrame
        """
        data = data.copy()
        
        # 计算价格变化
        delta = data[self.price_key].diff()
        
        # 分离上涨和下跌
        gain = delta.copy()
        loss = delta.copy()
        gain[gain < 0] = 0
        loss[loss > 0] = 0
        loss = -loss  # 转为正值
        
        # 计算平均涨跌幅
        avg_gain = gain.rolling(window=self.window).mean()
        avg_loss = loss.rolling(window=self.window).mean()
        
        # 计算相对强度
        rs = avg_gain / avg_loss
        
        # 计算RSI
        data[self.column_name] = 100 - (100 / (1 + rs))
        
        return data
    
    def get_signal(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """生成基于RSI的交易信号
        
        Args:
            data: 包含指标数据的DataFrame
            **kwargs: 其他参数
                - overbought: 超买阈值，默认为70
                - oversold: 超卖阈值，默认为30
                - signal_type: 信号类型，可以是'level'(价位)或'divergence'(背离)
            
        Returns:
            pd.DataFrame: 添加了交易信号列的DataFrame
        """
        # 确保指标已经计算
        if self.column_name not in data.columns:
            data = self.calculate(data)
            
        overbought = kwargs.get('overbought', 70)
        oversold = kwargs.get('oversold', 30)
        signal_type = kwargs.get('signal_type', 'level')
        
        if signal_type == 'level':
            # 基于价位的信号
            signal_column = f"{self.column_name}_level_signal"
            data[signal_column] = 0  # 默认无信号
            
            # 超卖区域反弹：买入信号
            data.loc[(data[self.column_name] > oversold) & 
                     (data[self.column_name].shift(1) <= oversold), signal_column] = 1
            
            # 超买区域回落：卖出信号
            data.loc[(data[self.column_name] < overbought) & 
                     (data[self.column_name].shift(1) >= overbought), signal_column] = -1
        
        elif signal_type == 'divergence':
            # 背离信号
            signal_column = f"{self.column_name}_divergence_signal"
            data[signal_column] = 0  # 默认无信号
            
            # 查找局部极值
            for i in range(5, len(data) - 5):
                # 价格出现高点但RSI没有创新高 -> 顶背离
                if (data[self.price_key].iloc[i] > data[self.price_key].iloc[i-1] and 
                    data[self.price_key].iloc[i] > data[self.price_key].iloc[i+1] and
                    data[self.price_key].iloc[i] > data[self.price_key].iloc[i-5] and
                    data[self.column_name].iloc[i] < data[self.column_name].iloc[i-5]):
                    data[signal_column].iloc[i] = -1
                
                # 价格出现低点但RSI没有创新低 -> 底背离
                elif (data[self.price_key].iloc[i] < data[self.price_key].iloc[i-1] and 
                      data[self.price_key].iloc[i] < data[self.price_key].iloc[i+1] and
                      data[self.price_key].iloc[i] < data[self.price_key].iloc[i-5] and
                      data[self.column_name].iloc[i] > data[self.column_name].iloc[i-5]):
                    data[signal_column].iloc[i] = 1
        
        return data
    
    def get_description(self) -> str:
        """获取指标的描述
        
        Returns:
            str: 指标描述
        """
        return f"相对强弱指数(RSI)，周期={self.window}"


class KDJ(IndicatorBase):
    """KDJ随机指标"""
    
    def __init__(self, k_window: int = 9, d_window: int = 3, j_window: int = 3):
        """初始化KDJ指标
        
        Args:
            k_window: K值周期
            d_window: D值周期
            j_window: J值周期
        """
        super().__init__('kdj')
        self.k_window = k_window
        self.d_window = d_window
        self.j_window = j_window
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """计算KDJ指标
        
        Args:
            data: 包含OHLCV数据的DataFrame
            **kwargs: 其他参数
            
        Returns:
            pd.DataFrame: 添加了KDJ指标列的DataFrame
        """
        data = data.copy()
        
        # 获取最高价和最低价
        high_prices = data['high']
        low_prices = data['low']
        close_prices = data['close']
        
        # 计算最近k_window周期内的最高价和最低价
        lowest_low = low_prices.rolling(window=self.k_window).min()
        highest_high = high_prices.rolling(window=self.k_window).max()
        
        # 计算RSV值
        rsv = 100 * ((close_prices - lowest_low) / (highest_high - lowest_low))
        
        # 计算K值
        data['kdj_k'] = rsv.ewm(alpha=1/self.d_window, adjust=False).mean()
        
        # 计算D值
        data['kdj_d'] = data['kdj_k'].ewm(alpha=1/self.j_window, adjust=False).mean()
        
        # 计算J值
        data['kdj_j'] = 3 * data['kdj_k'] - 2 * data['kdj_d']
        
        return data
    
    def get_signal(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """生成基于KDJ的交易信号
        
        Args:
            data: 包含指标数据的DataFrame
            **kwargs: 其他参数
                - overbought: 超买阈值，默认为80
                - oversold: 超卖阈值，默认为20
                - signal_type: 信号类型，可以是'cross'(交叉)或'level'(价位)
            
        Returns:
            pd.DataFrame: 添加了交易信号列的DataFrame
        """
        # 确保指标已经计算
        if 'kdj_k' not in data.columns:
            data = self.calculate(data)
            
        overbought = kwargs.get('overbought', 80)
        oversold = kwargs.get('oversold', 20)
        signal_type = kwargs.get('signal_type', 'cross')
        
        if signal_type == 'cross':
            # 基于KD线交叉的信号
            data['kdj_cross_signal'] = 0  # 默认无信号
            
            # K线上穿D线：买入信号
            data.loc[(data['kdj_k'] > data['kdj_d']) & 
                     (data['kdj_k'].shift(1) <= data['kdj_d'].shift(1)), 'kdj_cross_signal'] = 1
            
            # K线下穿D线：卖出信号
            data.loc[(data['kdj_k'] < data['kdj_d']) & 
                     (data['kdj_k'].shift(1) >= data['kdj_d'].shift(1)), 'kdj_cross_signal'] = -1
        
        elif signal_type == 'level':
            # 基于超买超卖水平的信号
            data['kdj_level_signal'] = 0  # 默认无信号
            
            # 超卖区域的K值反弹：买入信号
            data.loc[(data['kdj_k'] > oversold) & 
                     (data['kdj_k'].shift(1) <= oversold), 'kdj_level_signal'] = 1
            
            # 超买区域的K值回落：卖出信号
            data.loc[(data['kdj_k'] < overbought) & 
                     (data['kdj_k'].shift(1) >= overbought), 'kdj_level_signal'] = -1
        
        return data
    
    def get_description(self) -> str:
        """获取指标的描述
        
        Returns:
            str: 指标描述
        """
        return f"KDJ随机指标，K周期={self.k_window}，D周期={self.d_window}，J周期={self.j_window}"


class VolumeProfile(IndicatorBase):
    """成交量指标"""
    
    def __init__(self, window: int = 20):
        """初始化成交量指标
        
        Args:
            window: 窗口大小
        """
        super().__init__('volume')
        self.window = window
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """计算成交量指标
        
        Args:
            data: 包含OHLCV数据的DataFrame
            **kwargs: 其他参数
            
        Returns:
            pd.DataFrame: 添加了成交量指标列的DataFrame
        """
        data = data.copy()
        
        # 计算成交量移动平均
        data['volume_ma'] = data['volume'].rolling(window=self.window).mean()
        
        # 计算成交量变化率
        data['volume_change'] = data['volume'].pct_change() * 100
        
        # 计算成交量相对强度
        data['volume_ratio'] = data['volume'] / data['volume_ma']
        
        # 识别主动买入/卖出成交量
        # 如果当前价格上涨，则视为主动买入，否则视为主动卖出
        data['buying_volume'] = data['volume'] * (data['close'] >= data['open']).astype(int)
        data['selling_volume'] = data['volume'] * (data['close'] < data['open']).astype(int)
        
        # 计算主动买入/卖出比率
        data['buy_sell_ratio'] = data['buying_volume'].rolling(window=self.window).sum() / \
                                data['selling_volume'].rolling(window=self.window).sum()
        
        return data
    
    def get_signal(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """生成基于成交量的交易信号
        
        Args:
            data: 包含指标数据的DataFrame
            **kwargs: 其他参数
                - volume_surge: 成交量突增阈值，默认为2.0
                - signal_type: 信号类型，可以是'surge'(突增)或'divergence'(背离)
            
        Returns:
            pd.DataFrame: 添加了交易信号列的DataFrame
        """
        # 确保指标已经计算
        if 'volume_ma' not in data.columns:
            data = self.calculate(data)
            
        volume_surge = kwargs.get('volume_surge', 2.0)
        signal_type = kwargs.get('signal_type', 'surge')
        
        if signal_type == 'surge':
            # 基于成交量突增的信号
            data['volume_surge_signal'] = 0  # 默认无信号
            
            # 成交量突增且价格上涨：买入信号
            data.loc[(data['volume_ratio'] > volume_surge) & 
                     (data['close'] > data['open']), 'volume_surge_signal'] = 1
            
            # 成交量突增且价格下跌：卖出信号
            data.loc[(data['volume_ratio'] > volume_surge) & 
                     (data['close'] < data['open']), 'volume_surge_signal'] = -1
        
        elif signal_type == 'divergence':
            # 价量背离信号
            data['volume_divergence_signal'] = 0  # 默认无信号
            
            # 价格上涨但成交量下降：卖出信号（顶部警示）
            data.loc[(data['close'] > data['close'].shift(1)) & 
                     (data['volume'] < data['volume'].shift(1)) &
                     (data['volume'].shift(1) < data['volume'].shift(2)), 'volume_divergence_signal'] = -1
            
            # 价格下跌但成交量下降：买入信号（底部警示）
            data.loc[(data['close'] < data['close'].shift(1)) & 
                     (data['volume'] < data['volume'].shift(1)) &
                     (data['volume'].shift(1) < data['volume'].shift(2)), 'volume_divergence_signal'] = 1
        
        return data
    
    def get_description(self) -> str:
        """获取指标的描述
        
        Returns:
            str: 指标描述
        """
        return f"成交量分析指标，周期={self.window}"