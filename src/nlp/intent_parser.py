"""
意图解析器，用于分析用户自然语言输入，识别意图和提取参数
"""
import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple

from src.nlp.llm_client import LLMFactory
from config.constants import (
    CMD_ANALYZE, CMD_SCREEN, CMD_TRADE, CMD_BACKTEST, CMD_MONITOR,
    MARKET_TYPE_A_SHARE, MARKET_TYPE_US, MARKET_TYPE_HK, MARKET_TYPE_CRYPTO,
    TIMEFRAME_1M, TIMEFRAME_5M, TIMEFRAME_15M, TIMEFRAME_30M,
    TIMEFRAME_1H, TIMEFRAME_4H, TIMEFRAME_1D, TIMEFRAME_1W,
    INDICATOR_MA, INDICATOR_EMA, INDICATOR_MACD, INDICATOR_RSI,
    INDICATOR_BOLLINGER, INDICATOR_KDJ, INDICATOR_VOLUME,
    STRATEGY_MACD_CROSS, STRATEGY_MA_CROSS, STRATEGY_RSI_OVERBOUGHT,
    STRATEGY_BREAKOUT, STRATEGY_GRID, STRATEGY_MARTINGALE,
    NLP_MODEL_DEEPSEEK
)


class IntentParser:
    """自然语言意图解析器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化意图解析器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.llm_client = LLMFactory.create_client(NLP_MODEL_DEEPSEEK, config_path=config_path)
        
        # 常见股票市场和代码前缀映射
        self.market_prefixes = {
            MARKET_TYPE_A_SHARE: ['SH', 'SZ', '沪市', '深市', 'A股'],
            MARKET_TYPE_HK: ['HK', '港股'],
            MARKET_TYPE_US: ['US', 'NYSE', 'NASDAQ', '美股'],
            MARKET_TYPE_CRYPTO: ['BTC', 'ETH', 'USDT', '币安', '加密货币', '数字货币']
        }
        
        # 常见时间周期表达方式
        self.timeframe_patterns = {
            TIMEFRAME_1M: [r'1分钟', r'一分钟', r'分钟线'],
            TIMEFRAME_5M: [r'5分钟', r'五分钟'],
            TIMEFRAME_15M: [r'15分钟', r'十五分钟'],
            TIMEFRAME_30M: [r'30分钟', r'三十分钟', r'半小时'],
            TIMEFRAME_1H: [r'1小时', r'一小时', r'小时线', r'60分钟'],
            TIMEFRAME_4H: [r'4小时', r'四小时'],
            TIMEFRAME_1D: [r'日线', r'天线', r'日K', r'每日', r'一天'],
            TIMEFRAME_1W: [r'周线', r'周K', r'星期', r'一周', r'每周']
        }
        
        # 指标关键词
        self.indicator_keywords = {
            INDICATOR_MA: ['均线', '移动平均线', 'MA', '均价'],
            INDICATOR_EMA: ['指数移动平均线', 'EMA'],
            INDICATOR_MACD: ['MACD', '指数平滑异同平均线', '金叉', '死叉'],
            INDICATOR_RSI: ['RSI', '相对强弱指标', '超买', '超卖'],
            INDICATOR_BOLLINGER: ['布林带', '布林线', 'BOLL', 'Bollinger'],
            INDICATOR_KDJ: ['KDJ', '随机指标'],
            INDICATOR_VOLUME: ['成交量', '量能', 'VOL', '成交额']
        }
        
        # 策略关键词
        self.strategy_keywords = {
            STRATEGY_MACD_CROSS: ['MACD金叉', 'MACD死叉', '金叉策略'],
            STRATEGY_MA_CROSS: ['均线交叉', '均线金叉', '均线死叉', '双均线'],
            STRATEGY_RSI_OVERBOUGHT: ['RSI超买', 'RSI超卖', 'RSI反转'],
            STRATEGY_BREAKOUT: ['突破', '突破策略', '压力位', '支撑位', '突破新高'],
            STRATEGY_GRID: ['网格', '网格交易', '等距网格'],
            STRATEGY_MARTINGALE: ['马丁', '马丁策略', '加倍策略']
        }
        
        # 命令类型关键词
        self.command_keywords = {
            CMD_ANALYZE: ['分析', '研究', '解读', '评估', '如何看'],
            CMD_SCREEN: ['筛选', '寻找', '查找', '过滤', '找出', '有哪些', '推荐'],
            CMD_TRADE: ['买入', '卖出', '交易', '下单', '建仓', '平仓', '止损'],
            CMD_BACKTEST: ['回测', '测试', '模拟', '历史表现'],
            CMD_MONITOR: ['监控', '提醒', '预警', '关注']
        }
    
    def _extract_market(self, text: str) -> str:
        """从文本中提取市场类型
        
        Args:
            text: 用户输入文本
            
        Returns:
            str: 市场类型
        """
        for market, prefixes in self.market_prefixes.items():
            for prefix in prefixes:
                if prefix in text:
                    return market
        return ""
    
    def _extract_timeframe(self, text: str) -> str:
        """从文本中提取时间周期
        
        Args:
            text: 用户输入文本
            
        Returns:
            str: 时间周期
        """
        for timeframe, patterns in self.timeframe_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    return timeframe
        return TIMEFRAME_1D  # 默认使用日线
    
    def _extract_indicators(self, text: str) -> List[str]:
        """从文本中提取技术指标
        
        Args:
            text: 用户输入文本
            
        Returns:
            List[str]: 技术指标列表
        """
        indicators = []
        for indicator, keywords in self.indicator_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    indicators.append(indicator)
                    break
        return indicators
    
    def _extract_strategies(self, text: str) -> List[str]:
        """从文本中提取交易策略
        
        Args:
            text: 用户输入文本
            
        Returns:
            List[str]: 交易策略列表
        """
        strategies = []
        for strategy, keywords in self.strategy_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    strategies.append(strategy)
                    break
        return strategies
    
    def _extract_command_type(self, text: str) -> str:
        """从文本中提取命令类型
        
        Args:
            text: 用户输入文本
            
        Returns:
            str: 命令类型
        """
        for cmd, keywords in self.command_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return cmd
        return CMD_ANALYZE  # 默认为分析命令
    
    def _extract_symbols(self, text: str) -> List[str]:
        """从文本中提取股票/加密货币符号
        
        Args:
            text: 用户输入文本
            
        Returns:
            List[str]: 符号列表
        """
        # 基本的股票代码匹配模式
        stock_patterns = [
            r'[A-Z]{1,5}\.[A-Z0-9]{1,8}',  # HK.00700, US.AAPL
            r'[A-Z]{1,5}/[A-Z]{1,5}',      # BTC/USDT
            r'[0-9]{6}',                   # 600000 (A股)
            r'[A-Z]{1,5}'                   # AAPL, GOOGL
        ]
        
        symbols = []
        for pattern in stock_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # 排除常见的非股票代码
                if match not in ['MACD', 'RSI', 'EMA', 'KDJ']:
                    symbols.append(match)
        
        return symbols
    
    def _extract_parameters(self, text: str) -> Dict[str, Any]:
        """从文本中提取各种参数
        
        Args:
            text: 用户输入文本
            
        Returns:
            Dict: 参数字典
        """
        # 提取数字参数
        # 例如：查找涨幅超过5%的股票
        percentages = re.findall(r'(\d+(?:\.\d+)?)%', text)
        
        # 提取日期范围
        # 例如：分析过去30天的数据
        days = re.findall(r'过去(\d+)天', text)
        days.extend(re.findall(r'(\d+)天(?:以来)?', text))
        
        # 提取金额
        # 例如：投入10000元买入比特币
        amounts = re.findall(r'(\d+(?:\.\d+)?)(?:元|块钱|万元|万块)', text)
        
        # 汇总参数
        params = {}
        if percentages:
            params['percentage'] = float(percentages[0])
        if days:
            params['days'] = int(days[0])
        if amounts:
            amount = float(amounts[0])
            if '万' in text:
                amount *= 10000
            params['amount'] = amount
            
        return params
    
    def _analyze_with_llm(self, text: str) -> Dict[str, Any]:
        """使用大语言模型分析用户意图和参数
        
        Args:
            text: 用户输入文本
            
        Returns:
            Dict: 意图和参数
        """
        # 构建提示
        messages = [
            {"role": "system", "content": """你是一个金融交易助手，能够理解用户的投资和交易意图。
请分析用户的输入，提取以下信息：
1. 命令类型：分析(analyze)、筛选(screen)、交易(trade)、回测(backtest)或监控(monitor)
2. 市场类型：A股、港股、美股或加密货币
3. 股票代码或加密货币代码（如有）
4. 时间周期
5. 技术指标（如有）
6. 交易策略（如有）
7. 其他参数：如金额、百分比、天数等
请按JSON格式返回，不要有任何其他回复。"""},
            {"role": "user", "content": text}
        ]
        
        # 调用LLM获取分析结果
        response = self.llm_client.chat_completion(messages, temperature=0.2)
        
        try:
            # 提取LLM的分析结果
            content = response["choices"][0]["message"]["content"]
            
            # 尝试解析JSON
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                return json.loads(json_str)
            else:
                logging.warning(f"LLM响应中没有找到有效的JSON: {content}")
                return {}
        except Exception as e:
            logging.error(f"解析LLM响应失败: {e}")
            return {}
    
    def parse(self, text: str) -> Dict[str, Any]:
        """解析用户输入，识别意图和提取参数
        
        Args:
            text: 用户输入文本
            
        Returns:
            Dict: 包含意图和参数的字典
        """
        # 基本规则解析
        command_type = self._extract_command_type(text)
        market = self._extract_market(text)
        timeframe = self._extract_timeframe(text)
        indicators = self._extract_indicators(text)
        strategies = self._extract_strategies(text)
        symbols = self._extract_symbols(text)
        parameters = self._extract_parameters(text)
        
        # 获取LLM分析结果
        llm_result = self._analyze_with_llm(text)
        
        # 合并规则解析和LLM结果，优先使用LLM结果
        result = {
            "original_text": text,
            "command_type": llm_result.get("command_type", command_type),
            "market": llm_result.get("market_type", market),
            "timeframe": llm_result.get("time_period", timeframe),
            "indicators": llm_result.get("technical_indicators", indicators),
            "strategies": llm_result.get("trading_strategy", strategies),
            "symbols": llm_result.get("stock_code", symbols) or symbols,  # 确保有符号
            "parameters": {**parameters, **llm_result.get("other_parameters", {})}
        }
        
        return result