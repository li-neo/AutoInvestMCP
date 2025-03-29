"""
交易执行器，负责执行交易操作
"""
import time
import json
import logging
from typing import Dict, List, Any, Optional

from src.data_api.api_factory import APIFactory
from src.data_api.base_api import BaseAPI


class TradeExecutor:
    """交易执行器"""
    
    def __init__(self, api_factory: APIFactory):
        """初始化交易执行器
        
        Args:
            api_factory: API工厂实例
        """
        self.api_factory = api_factory
        self.trades = []  # 记录交易历史
        self.positions = {}  # 记录当前持仓
    
    def place_order(self, symbol: str, order_type: str, side: str, 
                    amount: float, price: Optional[float] = None) -> Dict[str, Any]:
        """下单交易
        
        Args:
            symbol: 交易对/股票代码
            order_type: 订单类型，如'LIMIT'、'MARKET'等
            side: 交易方向，'BUY'或'SELL'
            amount: 交易数量
            price: 交易价格，对于市价单可为None
            
        Returns:
            Dict: 订单信息
        """
        # 获取适合该交易对/股票的API
        api = self.api_factory.get_api_for_symbol(symbol)
        if not api:
            error_msg = f"找不到适合{symbol}的交易API"
            logging.error(error_msg)
            return {'error': error_msg}
        
        try:
            # 执行下单操作
            order_result = api.place_order(
                symbol=symbol,
                order_type=order_type,
                side=side,
                amount=amount,
                price=price
            )
            
            # 记录交易
            if order_result and 'order_id' in order_result:
                trade = {
                    'time': time.time(),
                    'symbol': symbol,
                    'order_type': order_type,
                    'side': side,
                    'amount': amount,
                    'price': price or 'market',
                    'order_id': order_result.get('order_id'),
                    'status': order_result.get('status')
                }
                self.trades.append(trade)
                
                # 更新持仓记录（简化版，实际应该等订单完成后更新）
                if side.upper() == 'BUY':
                    self.positions[symbol] = self.positions.get(symbol, 0) + amount
                elif side.upper() == 'SELL':
                    self.positions[symbol] = self.positions.get(symbol, 0) - amount
            
            return order_result
        except Exception as e:
            error_msg = f"下单失败: {e}"
            logging.error(error_msg)
            return {'error': error_msg}
    
    def cancel_order(self, order_id: str, symbol: str = None) -> Dict[str, Any]:
        """取消订单
        
        Args:
            order_id: 订单ID
            symbol: 交易对/股票代码，部分API需要提供
            
        Returns:
            Dict: 取消结果
        """
        # 如果没有提供symbol，尝试从交易历史中查找
        if not symbol:
            for trade in self.trades:
                if trade.get('order_id') == order_id:
                    symbol = trade.get('symbol')
                    break
            
            if not symbol:
                error_msg = f"取消订单需要提供symbol参数"
                logging.error(error_msg)
                return {'error': error_msg}
        
        # 获取适合该交易对/股票的API
        api = self.api_factory.get_api_for_symbol(symbol)
        if not api:
            error_msg = f"找不到适合{symbol}的交易API"
            logging.error(error_msg)
            return {'error': error_msg}
        
        try:
            # 取消订单
            # 注意：币安需要提供symbol，而富途不需要
            if hasattr(api, 'cancel_order') and 'binance' in api.__class__.__name__.lower():
                result = api.cancel_order(order_id=order_id, symbol=symbol)
            else:
                result = api.cancel_order(order_id=order_id)
            
            # 更新交易记录
            for trade in self.trades:
                if trade.get('order_id') == order_id:
                    trade['status'] = 'canceled'
            
            return {'success': result, 'order_id': order_id}
        except Exception as e:
            error_msg = f"取消订单失败: {e}"
            logging.error(error_msg)
            return {'error': error_msg}
    
    def get_order_status(self, order_id: str, symbol: str = None) -> Dict[str, Any]:
        """查询订单状态
        
        Args:
            order_id: 订单ID
            symbol: 交易对/股票代码，部分API需要提供
            
        Returns:
            Dict: 订单状态信息
        """
        # 如果没有提供symbol，尝试从交易历史中查找
        if not symbol:
            for trade in self.trades:
                if trade.get('order_id') == order_id:
                    symbol = trade.get('symbol')
                    break
            
            if not symbol:
                error_msg = f"查询订单状态需要提供symbol参数"
                logging.error(error_msg)
                return {'error': error_msg}
        
        # 获取适合该交易对/股票的API
        api = self.api_factory.get_api_for_symbol(symbol)
        if not api:
            error_msg = f"找不到适合{symbol}的交易API"
            logging.error(error_msg)
            return {'error': error_msg}
        
        try:
            # 查询订单状态
            # 注意：币安需要提供symbol，而富途不需要
            if hasattr(api, 'get_order_status') and 'binance' in api.__class__.__name__.lower():
                order_status = api.get_order_status(order_id=order_id, symbol=symbol)
            else:
                order_status = api.get_order_status(order_id=order_id)
            
            # 更新交易记录
            for trade in self.trades:
                if trade.get('order_id') == order_id:
                    trade['status'] = order_status.get('status')
            
            return order_status
        except Exception as e:
            error_msg = f"查询订单状态失败: {e}"
            logging.error(error_msg)
            return {'error': error_msg}
    
    def get_account_info(self, api_type: str = None) -> Dict[str, Any]:
        """获取账户信息
        
        Args:
            api_type: API类型，如'binance'或'futu'
        
        Returns:
            Dict: 账户信息
        """
        result = {}
        
        if api_type:
            # 获取指定类型的API
            api = self.api_factory.get_api(api_type)
            if not api:
                error_msg = f"找不到类型为{api_type}的API"
                logging.error(error_msg)
                return {'error': error_msg}
            
            try:
                account_info = api.get_account_info()
                result[api_type] = account_info
            except Exception as e:
                error_msg = f"获取{api_type}账户信息失败: {e}"
                logging.error(error_msg)
                result[api_type] = {'error': error_msg}
        else:
            # 获取所有已连接API的账户信息
            apis = {}
            
            # 尝试获取常用API
            for api_name in ['binance', 'futu']:
                api = self.api_factory.get_api(api_name)
                if api:
                    apis[api_name] = api
            
            # 获取每个API的账户信息
            for api_name, api in apis.items():
                try:
                    account_info = api.get_account_info()
                    result[api_name] = account_info
                except Exception as e:
                    error_msg = f"获取{api_name}账户信息失败: {e}"
                    logging.error(error_msg)
                    result[api_name] = {'error': error_msg}
        
        return result
    
    def execute_order_list(self, orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """执行一组订单
        
        Args:
            orders: 订单列表，每个元素是一个字典，包含订单信息
        
        Returns:
            List[Dict]: 执行结果列表
        """
        results = []
        
        for order in orders:
            symbol = order.get('symbol')
            order_type = order.get('order_type', 'MARKET')
            side = order.get('side')
            amount = order.get('amount')
            price = order.get('price')
            
            # 验证必要参数
            if not symbol or not side or not amount:
                results.append({
                    'error': '订单缺少必要参数',
                    'order': order
                })
                continue
            
            # 执行订单
            result = self.place_order(
                symbol=symbol,
                order_type=order_type,
                side=side,
                amount=amount,
                price=price
            )
            
            results.append({
                'order': order,
                'result': result
            })
        
        return results
    
    def get_trade_history(self) -> List[Dict[str, Any]]:
        """获取交易历史
        
        Returns:
            List[Dict]: 交易历史
        """
        return self.trades
    
    def get_positions(self) -> Dict[str, float]:
        """获取当前持仓
        
        Returns:
            Dict: 持仓信息，键为交易对/股票代码，值为持仓量
        """
        return self.positions