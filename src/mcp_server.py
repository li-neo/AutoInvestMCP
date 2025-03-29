"""
MCP服务主入口，提供API接口
"""
import os
import json
import logging
import argparse
from typing import Dict, Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.mcp_handler import MCPHandler


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("autoinvest.log")
    ]
)

# 创建FastAPI应用
app = FastAPI(
    title="AutoInvestAI - 智能投资助手",
    description="通过自然语言处理实现智能投资分析和交易",
    version="1.0.0"
)

# 添加CORS支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局MCP处理器实例
mcp_handler = None


# 请求模型
class MCPRequest(BaseModel):
    """MCP请求模型"""
    query: str = Field(..., description="用户查询文本")
    user_id: Optional[str] = Field(None, description="用户标识")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")


# 响应模型
class MCPResponse(BaseModel):
    """MCP响应模型"""
    success: bool = Field(..., description="请求是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[Dict[str, Any]] = Field(None, description="响应数据")
    query: str = Field(..., description="原始查询文本")


# 初始化MCP处理器
def get_mcp_handler():
    """获取MCP处理器实例
    
    Returns:
        MCPHandler: MCP处理器实例
    """
    global mcp_handler
    
    if mcp_handler is None:
        # 获取配置路径
        config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
        config_path = os.path.join(config_dir, "config.json")
        
        # 创建MCP处理器
        mcp_handler = MCPHandler(config_path)
    
    return mcp_handler


# API路由
@app.post("/api/query", response_model=MCPResponse)
async def process_query(request: MCPRequest, handler: MCPHandler = Depends(get_mcp_handler)):
    """处理用户查询
    
    Args:
        request: 用户请求
        handler: MCP处理器实例
        
    Returns:
        MCPResponse: 处理结果
    """
    try:
        # 处理请求
        result = handler.process_request(request.query)
        
        return {
            "success": result.get("success", False),
            "message": result.get("message", "处理完成"),
            "data": result.get("data"),
            "query": request.query
        }
    except Exception as e:
        logging.error(f"处理查询出错: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """健康检查接口
    
    Returns:
        Dict: 健康状态
    """
    return {
        "status": "ok",
        "version": "1.0.0"
    }


def parse_args():
    """解析命令行参数
    
    Returns:
        argparse.Namespace: 解析后的参数
    """
    parser = argparse.ArgumentParser(description="AutoInvestAI MCP服务")
    parser.add_argument("--host", default="0.0.0.0", help="服务主机地址")
    parser.add_argument("--port", type=int, default=8000, help="服务端口")
    parser.add_argument("--config", default="../config/config.json", help="配置文件路径")
    
    return parser.parse_args()


if __name__ == "__main__":
    # 解析命令行参数
    args = parse_args()
    
    # 读取配置中的服务设置
    try:
        with open(args.config, 'r') as f:
            config = json.load(f)
            server_config = config.get('server', {})
            host = server_config.get('host', args.host)
            port = server_config.get('port', args.port)
    except:
        host = args.host
        port = args.port
    
    # 启动服务
    logging.info(f"启动AutoInvestAI MCP服务，地址: {host}:{port}")
    uvicorn.run(app, host=host, port=port)