"""
大语言模型客户端，用于自然语言处理
"""
import os
import json
import logging
import requests
import time
from typing import Dict, List, Any, Optional, Union
from dotenv import load_dotenv

# 这里需要根据实际情况导入DeepSeek SDK
# 由于目前DeepSeek可能没有官方Python SDK，我们使用通用接口设计
# 实际使用时可替换为官方SDK或适当的API实现
try:
    # 尝试导入OpenAI SDK
    from openai import OpenAI
except ImportError:
    pass


class LLMClient:
    """LLM客户端基类"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化客户端基类
        
        Args:
            config_path: 配置文件路径
        """
        # 加载环境变量
        load_dotenv()
        
        self.config = {}
        
        # 如果未提供配置路径，尝试默认路径
        if config_path is None:
            # 项目根目录下的配置
            root_config = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                      "config", "config.json")
            if os.path.exists(root_config):
                config_path = root_config
        
        # 加载配置
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except Exception as e:
                logging.error(f"加载配置文件失败: {e}")
        else:
            logging.warning(f"配置文件不存在: {config_path}")
            self.config = {}
    
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """向LLM发送对话请求
        
        Args:
            messages: 对话历史消息列表
            **kwargs: 其他参数，如temperature, max_tokens等
            
        Returns:
            Dict: LLM响应结果
        """
        raise NotImplementedError("子类必须实现此方法")


class DeepSeekClient(LLMClient):
    """DeepSeek模型客户端"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化DeepSeek客户端
        
        Args:
            config_path: 配置文件路径
        """
        super().__init__(config_path)
        
        # 优先从环境变量读取API密钥，如果不存在则从配置文件读取
        self.api_key = os.environ.get('DEEPSEEK_API_KEY') or self.config.get('nlp', {}).get('deepseek', {}).get('api_key', '')
        
        if not self.api_key:
            logging.warning("未找到DeepSeek API密钥，将使用备用响应")
    
    def chat_completion(self, messages: List[Dict[str, str]], 
                        model: str = "deepseek-chat", 
                        temperature: float = 0.7, 
                        max_tokens: int = 1000) -> Dict[str, Any]:
        """向DeepSeek发送对话请求
        
        Args:
            messages: 对话历史消息列表
            model: 模型名称
            temperature: 温度参数，控制随机性
            max_tokens: 生成的最大token数
            
        Returns:
            Dict: DeepSeek响应结果
        """
        try:
            # 检查API密钥是否存在
            if not self.api_key:
                logging.warning("未找到DeepSeek API密钥，将使用备用响应")
                return self._generate_fallback_response(messages)
            
            # API请求URL和头信息
            api_url = "https://api.deepseek.com/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # 构建请求数据
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "response_format": {"type": "json_object"}  # 确保返回JSON格式
            }
            
            # 发送API请求
            logging.info(f"向DeepSeek API发送请求: {api_url}")
            response = requests.post(api_url, headers=headers, json=payload)
            response.raise_for_status()  # 如果请求失败，抛出异常
            
            # 解析响应
            api_response = response.json()
            logging.debug(f"DeepSeek API响应: {api_response}")
            
            return api_response
            
        except Exception as e:
            logging.error(f"DeepSeek API请求失败: {e}")
            # 返回错误消息
            return self._generate_error_response(str(e), model)
    
    def _generate_fallback_response(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """当API密钥不可用时生成备用响应
        
        Args:
            messages: 对话历史消息列表
            
        Returns:
            Dict: 备用响应
        """
        # 获取最后一条用户消息的内容
        user_query = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_query = msg.get("content", "").lower()
                break
        
        # 根据用户查询确定命令类型
        command_type = "analyze"  # 默认分析
        
        if any(word in user_query for word in ["筛选", "寻找", "查找", "过滤", "找出", "有哪些", "推荐"]):
            command_type = "screen"
        elif any(word in user_query for word in ["买入", "卖出", "交易", "下单", "建仓", "平仓", "止损"]):
            command_type = "trade"
        elif any(word in user_query for word in ["回测", "测试", "模拟", "历史表现"]):
            command_type = "backtest"
        elif any(word in user_query for word in ["监控", "提醒", "预警", "关注"]):
            command_type = "monitor"
        
        # 根据用户查询判断市场类型
        market_type = "US"  # 默认是美股
        if any(word in user_query for word in ["a股", "a股", "A股", "沪深", "沪市", "深市", "中国", "国内"]):
            market_type = "A股"
        elif any(word in user_query for word in ["港股", "香港"]):
            market_type = "港股"
        elif any(word in user_query for word in ["加密", "比特币", "以太坊", "币"]):
            market_type = "加密货币"
        
        # 备用响应数据
        mock_response = {
            "command_type": command_type,
            "market": market_type,
            "timeframe": "1d",
            "indicators": ["macd", "rsi"],
            "strategies": ["ma_cross"],
            "symbols": ["AAPL", "MSFT", "GOOGL", "BABA", "BTC", "00700", "600519"],
            "parameters": {
                "days": 30,
                "amount": 10000
            }
        }
        
        # 包装为API响应格式
        return {
            "id": f"fallback-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "fallback-model",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(mock_response)
                    },
                    "index": 0,
                    "finish_reason": "stop"
                }
            ]
        }
    
    def _generate_error_response(self, error_message: str, model: str) -> Dict[str, Any]:
        """生成错误响应
        
        Args:
            error_message: 错误信息
            model: 模型名称
            
        Returns:
            Dict: 错误响应
        """
        error_response = {
            "error": error_message
        }
        
        return {
            "id": f"error-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(error_response)
                    },
                    "index": 0,
                    "finish_reason": "error"
                }
            ]
        }


class OpenAIClient(LLMClient):
    """OpenAI模型客户端"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化OpenAI客户端
        
        Args:
            config_path: 配置文件路径
        """
        super().__init__(config_path)
        
        # 优先从环境变量读取API密钥，如果不存在则从配置文件读取
        self.api_key = os.environ.get('OPENAI_API_KEY') or self.config.get('nlp', {}).get('openai', {}).get('api_key', '')
        
        if not self.api_key:
            logging.warning("未找到OpenAI API密钥，将使用备用响应")
    
    def chat_completion(self, messages: List[Dict[str, str]], 
                        model: str = "gpt-3.5-turbo", 
                        temperature: float = 0.7, 
                        max_tokens: int = 1000) -> Dict[str, Any]:
        """向OpenAI发送对话请求
        
        Args:
            messages: 对话历史消息列表
            model: 模型名称
            temperature: 温度参数，控制随机性
            max_tokens: 生成的最大token数
            
        Returns:
            Dict: OpenAI响应结果
        """
        try:
            # 检查API密钥是否存在
            if not self.api_key:
                logging.warning("未找到OpenAI API密钥，将使用备用响应")
                return self._generate_fallback_response(messages)
            
            # 导入openai库
            try:
                import openai
                openai.api_key = self.api_key
            except ImportError:
                logging.error("未安装openai库，请运行 pip install openai")
                return self._generate_error_response("未安装openai库", model)
            
            # 发送API请求
            logging.info(f"向OpenAI API发送请求，使用模型: {model}")
            response = openai.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"}
            )
            
            # 将响应转换为字典
            api_response = response.model_dump()
            logging.debug(f"OpenAI API响应: {api_response}")
            
            return api_response
            
        except Exception as e:
            logging.error(f"OpenAI API请求失败: {e}")
            return self._generate_error_response(str(e), model)
    
    def _generate_fallback_response(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """当API密钥不可用时生成备用响应
        
        Args:
            messages: 对话历史消息列表
            
        Returns:
            Dict: 备用响应
        """
        # 获取最后一条用户消息的内容
        user_query = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_query = msg.get("content", "").lower()
                break
        
        # 根据用户查询确定命令类型
        command_type = "analyze"  # 默认分析
        
        if any(word in user_query for word in ["筛选", "寻找", "查找", "过滤", "找出", "有哪些", "推荐"]):
            command_type = "screen"
        elif any(word in user_query for word in ["买入", "卖出", "交易", "下单", "建仓", "平仓", "止损"]):
            command_type = "trade"
        elif any(word in user_query for word in ["回测", "测试", "模拟", "历史表现"]):
            command_type = "backtest"
        elif any(word in user_query for word in ["监控", "提醒", "预警", "关注"]):
            command_type = "monitor"
        
        # 根据用户查询判断市场类型
        market_type = "US"  # 默认是美股
        if any(word in user_query for word in ["a股", "a股", "A股", "沪深", "沪市", "深市", "中国", "国内"]):
            market_type = "A股"
        elif any(word in user_query for word in ["港股", "香港"]):
            market_type = "港股"
        elif any(word in user_query for word in ["加密", "比特币", "以太坊", "币"]):
            market_type = "加密货币"
        
        # 备用响应数据
        mock_response = {
            "command_type": command_type,
            "market": market_type,
            "timeframe": "1d",
            "indicators": ["macd", "rsi"],
            "strategies": ["ma_cross"],
            "symbols": ["AAPL", "MSFT", "GOOGL", "BABA", "BTC", "00700", "600519"],
            "parameters": {
                "days": 30,
                "amount": 10000
            }
        }
        
        # 包装为API响应格式
        return {
            "id": f"fallback-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "fallback-model",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(mock_response)
                    },
                    "index": 0,
                    "finish_reason": "stop"
                }
            ]
        }
    
    def _generate_error_response(self, error_message: str, model: str) -> Dict[str, Any]:
        """生成错误响应
        
        Args:
            error_message: 错误信息
            model: 模型名称
            
        Returns:
            Dict: 错误响应
        """
        error_response = {
            "error": error_message
        }
        
        return {
            "id": f"error-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(error_response)
                    },
                    "index": 0,
                    "finish_reason": "error"
                }
            ]
        }


class LLMFactory:
    """LLM工厂类，用于创建不同类型的LLM客户端"""
    
    @staticmethod
    def create_client(llm_type: str, config_path: Optional[str] = None) -> LLMClient:
        """创建LLM客户端实例
        
        Args:
            llm_type: LLM类型
            config_path: 配置文件路径
            
        Returns:
            LLMClient: LLM客户端实例
        """
        if llm_type.lower() == 'deepseek':
            return DeepSeekClient(config_path)
        elif llm_type.lower() == 'openai':
            return OpenAIClient(config_path)
        else:
            raise ValueError(f"不支持的LLM类型: {llm_type}")