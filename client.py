"""
AutoInvestAI 命令行客户端
"""
import os
import sys
import json
import argparse
import requests
from typing import Dict, Any

# 默认服务器地址
DEFAULT_SERVER = 'http://localhost:8000'


def send_query(server_url: str, query: str) -> Dict[str, Any]:
    """发送查询到服务器
    
    Args:
        server_url: 服务器URL
        query: 查询文本
        
    Returns:
        Dict: 响应结果
    """
    url = f"{server_url}/api/query"
    
    # 构建请求数据
    data = {
        "query": query,
        "user_id": "cli_user",
        "context": {}
    }
    
    try:
        # 发送请求
        response = requests.post(url, json=data)
        response.raise_for_status()
        
        # 解析响应
        result = response.json()
        return result
    except requests.exceptions.RequestException as e:
        print(f"请求出错: {e}")
        return {
            "success": False,
            "message": f"请求出错: {str(e)}",
            "data": None,
            "query": query
        }


def print_result(result: Dict[str, Any]):
    """打印响应结果
    
    Args:
        result: 响应结果
    """
    # 打印基本信息
    print("\n" + "=" * 50)
    print(f"查询: {result['query']}")
    print(f"状态: {'成功' if result['success'] else '失败'}")
    print(f"消息: {result['message']}")
    print("=" * 50)
    
    # 打印数据
    data = result.get('data')
    if data:
        # 处理分析结果
        if 'screened_symbols' in data:
            # 筛选结果
            symbols = data['screened_symbols']
            print(f"\n找到 {len(symbols)} 个符合条件的股票:\n")
            for i, symbol in enumerate(symbols, 1):
                name = symbol.get('name', '')
                price = symbol.get('latest_price', 0)
                change = symbol.get('price_change_percent', 0)
                print(f"{i}. {symbol['symbol']} {name}: ¥{price:.2f} ({change:+.2f}%)")
        
        elif isinstance(data, dict) and any(isinstance(data.get(k), dict) for k in data):
            # 分析结果
            print("\n分析结果:\n")
            for symbol, info in data.items():
                if isinstance(info, dict) and info.get('success', False):
                    ticker_info = info.get('ticker_info', {})
                    name = ticker_info.get('name', '')
                    price = info.get('latest_price')
                    change = info.get('price_change_percent')
                    
                    print(f"\n{symbol} {name}:")
                    print(f"  最新价格: {'¥' if symbol.startswith(('SH', 'SZ')) else '$'}{price:.2f}")
                    if change is not None:
                        print(f"  涨跌幅: {change:+.2f}%")
                    
                    # 打印指标
                    indicators = info.get('indicators', {})
                    if indicators:
                        print("  技术指标:")
                        for ind_name, ind_values in indicators.items():
                            print(f"    {ind_name}: ", end="")
                            for k, v in ind_values.items():
                                print(f"{k}={v:.4f} ", end="")
                            print()
        
        elif 'trade_results' in data:
            # 交易结果
            trades = data['trade_results']
            print(f"\n交易结果:\n")
            for trade in trades:
                symbol = trade.get('symbol', '')
                success = trade.get('success', False)
                message = trade.get('message', '')
                
                status = "成功" if success else "失败"
                print(f"{symbol}: {status} - {message}")
        
        elif 'backtest_results' in data:
            # 回测结果
            backtest = data['backtest_results']
            print(f"\n回测结果:\n")
            for test in backtest:
                symbol = test.get('symbol', '')
                strategy = test.get('strategy', '')
                success = test.get('success', False)
                
                print(f"{symbol} 使用 {strategy} 策略:")
                if success and 'result' in test:
                    result = test['result']
                    print(f"  初始资金: ¥{result.get('initial_capital', 0):.2f}")
                    print(f"  最终资金: ¥{result.get('final_equity', 0):.2f}")
                    print(f"  总收益率: {result.get('total_return_pct', 0):.2f}%")
                    print(f"  年化收益: {result.get('annual_return_pct', 0):.2f}%")
                    print(f"  最大回撤: {result.get('max_drawdown_pct', 0):.2f}%")
                    print(f"  交易次数: {result.get('total_trades', 0)}")
                else:
                    print(f"  回测失败: {test.get('message', '')}")
        
        else:
            # 其他数据格式，直接打印
            print("\n数据:")
            print(json.dumps(data, indent=2, ensure_ascii=False))


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AutoInvestAI 命令行客户端")
    parser.add_argument("--server", default=DEFAULT_SERVER, help="服务器地址")
    parser.add_argument("query", nargs="?", help="查询文本")
    
    args = parser.parse_args()
    
    # 如果没有提供查询，进入交互模式
    if not args.query:
        print("欢迎使用 AutoInvestAI 命令行客户端！")
        print(f"连接到服务器: {args.server}")
        print("输入 'quit' 或 'exit' 退出。")
        
        while True:
            query = input("\n请输入您的查询: ")
            if query.lower() in ['quit', 'exit']:
                print("谢谢使用，再见！")
                break
            
            result = send_query(args.server, query)
            print_result(result)
    else:
        # 单次查询模式
        result = send_query(args.server, args.query)
        print_result(result)


if __name__ == "__main__":
    main()