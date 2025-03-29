"""
API工厂模块，用于创建和管理不同的数据API实例
"""
import os
import json
from typing import Dict, Optional

from src.data_api.base_api import BaseAPI
from src.data_api.binance_api import BinanceAPI
from src.data_api.futu_api import FutuAPI
from config.constants import MARKET_TYPE_CRYPTO, MARKET_TYPE_HK, MARKET_TYPE_US, MARKET_TYPE_A_SHARE


class APIFactory:
    """API工厂类，用于创建和管理不同的数据API实例"""
    
    def __init__(self, config_path: str):
        """初始化API工厂
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.apis = {}  # 存储API实例的字典
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """加载配置文件
        
        Returns:
            Dict: 配置信息
        """
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"加载配置文件失败: {e}")
            return {}
    
    def get_api(self, api_type: str, market: Optional[str] = None) -> Optional[BaseAPI]:
        """获取指定类型的API实例
        
        Args:
            api_type: API类型，例如 'binance', 'futu'
            market: 可选，对于支持多市场的API（如futu），指定市场类型
            
        Returns:
            BaseAPI: API实例，如果创建失败则返回None
        """
        # 生成API的唯一标识
        api_key = f"{api_type}_{market}" if market else api_type
        
        # 如果已经创建了API实例，直接返回
        if api_key in self.apis:
            return self.apis[api_key]
        
        # 创建新的API实例
        api = None
        
        if api_type.lower() == 'binance':
            api = self._create_binance_api()
        elif api_type.lower() == 'futu':
            api = self._create_futu_api(market)
        else:
            print(f"不支持的API类型: {api_type}")
            return None
        
        # 保存并返回API实例
        if api:
            self.apis[api_key] = api
            
        return api
    
    def _create_binance_api(self) -> Optional[BinanceAPI]:
        """创建币安API实例
        
        Returns:
            BinanceAPI: 币安API实例，如果创建失败则返回None
        """
        try:
            api = BinanceAPI(config_path=self.config_path)
            if api.connect():
                return api
            return None
        except Exception as e:
            print(f"创建币安API实例失败: {e}")
            return None
    
    def _create_futu_api(self, market: Optional[str] = None) -> Optional[FutuAPI]:
        """创建富途API实例
        
        Args:
            market: 可选，指定市场类型
            
        Returns:
            FutuAPI: 富途API实例，如果创建失败则返回None
        """
        try:
            # 如果没有指定市场，默认使用港股
            if not market:
                market = MARKET_TYPE_HK
                
            api = FutuAPI(config_path=self.config_path, market=market)
            if api.connect():
                return api
            return None
        except Exception as e:
            print(f"创建富途API实例失败: {e}")
            return None
    
    def get_api_for_symbol(self, symbol: str) -> Optional[BaseAPI]:
        """根据交易对/股票代码自动选择合适的API
        
        Args:
            symbol: 交易对/股票代码
            
        Returns:
            BaseAPI: 适合处理该交易对/股票的API实例
        """
        # 根据代码前缀判断市场
        if symbol.startswith(('HK.', 'HKEX.')):
            return self.get_api('futu', MARKET_TYPE_HK)
        elif symbol.startswith(('US.', 'NYSE.', 'NASDAQ.')):
            return self.get_api('futu', MARKET_TYPE_US)
        elif symbol.startswith(('SH.', 'SZ.', 'A.')):
            return self.get_api('futu', MARKET_TYPE_A_SHARE)
        elif '/' in symbol or symbol.endswith(('USDT', 'BTC', 'ETH')):
            return self.get_api('binance')
        else:
            # 无法确定市场，尝试使用默认API
            print(f"无法确定{symbol}的市场类型，尝试使用默认API")
            return self.get_api('futu')
            
    def close_all(self):
        """关闭所有API连接"""
        for api_key, api in self.apis.items():
            try:
                # 对于富途API需要特殊处理
                if isinstance(api, FutuAPI):
                    if api.quote_ctx:
                        api.quote_ctx.close()
                    if api.trade_ctx:
                        api.trade_ctx.close()
                print(f"已关闭 {api_key} 连接")
            except Exception as e:
                print(f"关闭 {api_key} 连接失败: {e}")
        
        # 清空API字典
        self.apis = {}