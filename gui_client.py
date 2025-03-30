"""
AutoInvestAI 图形界面客户端 - 基于Gradio实现
提供类似ChatGPT的聊天界面
"""
import os
import sys
import json
import requests
import argparse
import gradio as gr
from typing import Dict, Any, List

# 默认服务器地址
DEFAULT_SERVER = 'http://localhost:8000'

# 样式设置
THEME = gr.themes.Soft(
    primary_hue="blue",
    secondary_hue="gray",
    neutral_hue="gray",
    spacing_size=gr.themes.sizes.spacing_md,
    radius_size=gr.themes.sizes.radius_md,
    text_size=gr.themes.sizes.text_md,
)

class AutoInvestAIChat:
    """AutoInvestAI 聊天客户端类"""
    
    def __init__(self, server_url: str = DEFAULT_SERVER):
        """初始化客户端
        
        Args:
            server_url: 服务器URL
        """
        self.server_url = server_url
        self.chat_history = []
    
    def send_query(self, query: str) -> Dict[str, Any]:
        """发送查询到服务器
        
        Args:
            query: 查询文本
            
        Returns:
            Dict: 响应结果
        """
        url = f"{self.server_url}/api/query"
        
        # 构建请求数据
        data = {
            "query": query,
            "user_id": "gui_user",
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
            error_message = f"请求出错: {str(e)}"
            return {
                "success": False,
                "message": error_message,
                "data": None,
                "query": query
            }
    
    def format_response(self, response: Dict[str, Any]) -> str:
        """格式化响应内容为易读的文本
        
        Args:
            response: 响应数据
            
        Returns:
            str: 格式化后的文本
        """
        # 如果请求失败，直接返回错误信息
        if not response.get('success', False):
            return f"❌ {response.get('message', '未知错误')}"
        
        # 获取数据部分
        data = response.get('data', {})
        if not data:
            return response.get('message', '处理完成，但无返回数据')
        
        result_parts = []
        
        # 处理筛选结果
        if 'screened_symbols' in data:
            symbols = data['screened_symbols']
            result_parts.append(f"📊 找到 {len(symbols)} 个符合条件的股票:\n")
            
            for i, symbol in enumerate(symbols, 1):
                name = symbol.get('name', '')
                price = symbol.get('latest_price', 0)
                change = symbol.get('price_change_percent', 0)
                result_parts.append(
                    f"{i}. {symbol['symbol']} {name}: "
                    f"¥{price:.2f} ({change:+.2f}%)"
                )
        
        # 处理分析结果
        # elif isinstance(data, dict) and any(isinstance(data.get(k), dict) for k in data):
        #     result_parts.append("📈 分析结果:\n")
            
        #     for symbol, info in data.items():
        #         if isinstance(info, dict) and info.get('success', False):
        #             ticker_info = info.get('ticker_info', {})
        #             name = ticker_info.get('name', '')
        #             price = info.get('latest_price')
        #             change = info.get('price_change_percent')
                    
        #             symbol_parts = [f"\n**{symbol}** {name}:"]
                    
        #             if price is not None:
        #                 currency = '¥' if symbol.startswith(('SH', 'SZ')) else '$'
        #                 symbol_parts.append(f"- 最新价格: {currency}{price:.2f}")
                    
        #             if change is not None:
        #                 emoji = "🔼" if change > 0 else "🔽" if change < 0 else "➡️"
        #                 symbol_parts.append(f"- 涨跌幅: {emoji} {change:+.2f}%")
                    
        #             # 添加指标信息
        #             indicators = info.get('indicators', {})
        #             if indicators:
        #                 symbol_parts.append("- 技术指标:")
        #                 for ind_name, ind_values in indicators.items():
        #                     ind_text = f"  - {ind_name}: "
        #                     ind_details = []
        #                     for k, v in ind_values.items():
        #                         ind_details.append(f"{k}={v:.4f}")
        #                     ind_text += ", ".join(ind_details)
        #                     symbol_parts.append(ind_text)
                    
        #             result_parts.append("\n".join(symbol_parts))
        
        # 处理交易结果
        elif 'trade_results' in data:
            trades = data['trade_results']
            result_parts.append("💰 交易结果:\n")
            
            for trade in trades:
                symbol = trade.get('symbol', '')
                success = trade.get('success', False)
                message = trade.get('message', '')
                
                emoji = "✅" if success else "❌"
                result_parts.append(f"{emoji} {symbol}: {message}")
        
        # 处理回测结果
        elif 'backtest_results' in data:
            backtest = data['backtest_results']
            result_parts.append("🧪 回测结果:\n")
            
            for test in backtest:
                symbol = test.get('symbol', '')
                strategy = test.get('strategy', '')
                success = test.get('success', False)
                
                test_parts = [f"**{symbol}** 使用 **{strategy}** 策略:"]
                
                if success and 'result' in test:
                    result = test['result']
                    test_parts.extend([
                        f"- 初始资金: ¥{result.get('initial_capital', 0):.2f}",
                        f"- 最终资金: ¥{result.get('final_equity', 0):.2f}",
                        f"- 总收益率: {result.get('total_return_pct', 0):.2f}%",
                        f"- 年化收益: {result.get('annual_return_pct', 0):.2f}%",
                        f"- 最大回撤: {result.get('max_drawdown_pct', 0):.2f}%",
                        f"- 交易次数: {result.get('total_trades', 0)}次"
                    ])
                else:
                    test_parts.append(f"- ❌ 回测失败: {test.get('message', '')}")
                
                result_parts.append("\n".join(test_parts))
        
        # 其他类型的数据
        else:
            result_parts.append("🔍 结果:")
            result_parts.append("```json")
            result_parts.append(json.dumps(data, indent=2, ensure_ascii=False))
            result_parts.append("```")
        
        # 返回格式化后的文本
        return "\n".join(result_parts)
    
    def chat(self, message: str, history: List[List[str]]) -> List[Dict[str, str]]:
        """处理聊天消息并返回回复
        
        Args:
            message: 用户消息
            history: 聊天历史
            
        Returns:
            List[Dict[str, str]]: 助手回复，使用消息格式
        """
        # 发送查询到服务器
        response = self.send_query(message)
        
        # 格式化响应
        formatted_response = self.format_response(response)
        
        # 返回格式化的消息列表
        return [
            {"role": "user", "content": message},
            {"role": "assistant", "content": formatted_response}
        ]


def create_chat_interface(server_url: str = DEFAULT_SERVER) -> gr.Blocks:
    """创建聊天界面
    
    Args:
        server_url: 服务器URL
        
    Returns:
        gr.Blocks: Gradio界面
    """
    # 创建聊天客户端
    client = AutoInvestAIChat(server_url)
    
    # 创建界面
    with gr.Blocks(theme=THEME) as interface:
        gr.Markdown("# 🤖 AutoInvestAI 智能投资助手")
        gr.Markdown("欢迎使用智能投资助手，您可以询问关于股票分析、筛选、回测和交易等问题。")
        
        chatbot = gr.Chatbot(
            height=500,
            avatar_images=(None, "🤖"),
            show_copy_button=True,
            type="messages"
        )
        
        with gr.Row():
            msg = gr.Textbox(
                placeholder="在这里输入您的问题，例如：筛选最近MACD金叉的A股股票",
                scale=9,
                container=False,
                show_label=False,
            )
            submit = gr.Button("发送", scale=1, variant="primary")
        
        gr.Markdown("### 🌟 示例问题")
        with gr.Row():
            gr.Examples(
                examples=[
                    ["分析腾讯股票的MACD和RSI指标"],
                    ["筛选最近MACD金叉的A股股票"],
                    ["回测茅台股票的均线交叉策略"],
                    ["买入10000元比特币"],
                    ["设置监控提醒，当苹果股票跌破150美元时通知我"],
                ],
                inputs=msg,
            )
        
        # 绑定事件
        submit_event = msg.submit(
            client.chat, 
            inputs=[msg, chatbot], 
            outputs=chatbot,
            queue=False,
        ).then(
            lambda: "", 
            None, 
            msg, 
            queue=False,
        )
        
        submit.click(
            client.chat,
            inputs=[msg, chatbot],
            outputs=chatbot,
            queue=False,
        ).then(
            lambda: "",
            None,
            msg,
            queue=False,
        )
        
        # 键盘快捷键
        interface.load(lambda: None, None, None, js="""
            () => {
                document.addEventListener('keydown', function(e) {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        const textbox = document.querySelector('input[data-testid="textbox"]');
                        if (textbox === document.activeElement && textbox.value.trim() !== '') {
                            const submitButton = document.querySelector('button[data-testid="button"]');
                            submitButton.click();
                            e.preventDefault();
                        }
                    }
                });
            }
        """)
    
    return interface


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AutoInvestAI 图形界面客户端")
    parser.add_argument("--server", default=DEFAULT_SERVER, help="服务器地址")
    parser.add_argument("--share", action="store_true", help="创建公开链接")
    parser.add_argument("--port", type=int, default=7860, help="本地端口")
    
    args = parser.parse_args()
    
    # 打印欢迎信息
    print(f"🤖 启动 AutoInvestAI 图形界面客户端")
    print(f"📡 连接到服务器: {args.server}")
    
    # 创建并启动界面
    chat_interface = create_chat_interface(args.server)
    chat_interface.launch(
        server_name="0.0.0.0",
        server_port=args.port,
        share=args.share,
        inbrowser=True,
    )


if __name__ == "__main__":
    main()