"""
Server酱3推送模块（客户端版本）
文档: https://doc.sc3.ft07.com/zh/serverchan3/server/api
"""
import os
import re
import requests
from typing import Optional, Dict, Any
from datetime import datetime

# Server酱3配置
SERVERCHAN_KEY = os.getenv('SERVERCHAN_KEY', '')


def extract_uid_from_sendkey(sendkey: str) -> str:
    """从SendKey中提取uid"""
    # SendKey格式: sctp{uid}t...
    match = re.match(r'^sctp(\d+)t', sendkey)
    if match:
        return match.group(1)
    raise ValueError(f"无法从SendKey中提取uid: {sendkey}")


class ServerChanPush:
    """Server酱3推送封装"""
    
    def __init__(self, send_key: str = None):
        self.send_key = send_key or SERVERCHAN_KEY
        
        if not self.send_key:
            raise ValueError("请设置Server酱SendKey (SERVERCHAN_KEY)")
        
        # 提取uid构建API地址
        self.uid = extract_uid_from_sendkey(self.send_key)
        self.api_url = f"https://{self.uid}.push.ft07.com/send/{self.send_key}.send"
    
    def send(self, title: str, desp: str = '', short: str = '', tags: str = '') -> Dict[str, Any]:
        """
        发送消息
        
        Args:
            title: 消息标题（必填）
            desp: 消息正文，支持Markdown（可选）
            short: 简短描述，用于卡片显示（可选）
            tags: 标签，多个用竖线分隔（可选）
        
        Returns:
            API响应
        """
        # 标题长度限制
        if len(title) > 100:
            title = title[:97] + '...'
        
        data = {
            'title': title,
            'desp': desp,
        }
        
        if short:
            data['short'] = short
        if tags:
            data['tags'] = tags
        
        try:
            response = requests.post(self.api_url, data=data, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            # Server酱3返回格式: {"code": 0, "message": "success", "data": {...}}
            if result.get('code') != 0:
                return {
                    'success': False,
                    'error': result.get('message', '未知错误'),
                    'code': result.get('code')
                }
            
            return {
                'success': True,
                'message': '推送成功',
                'push_time': datetime.now().isoformat(),
                'data': result.get('data', {})
            }
        
        except requests.exceptions.Timeout:
            return {'success': False, 'error': '推送超时'}
        except requests.exceptions.RequestException as e:
            return {'success': False, 'error': f'推送失败: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': f'未知错误: {str(e)}'}


# 便捷函数
def send_message(title: str, desp: str = '', short: str = '', tags: str = '') -> Dict[str, Any]:
    """发送消息"""
    push = ServerChanPush()
    return push.send(title, desp, short=short, tags=tags)


if __name__ == '__main__':
    # 测试
    import dotenv
    dotenv.load_dotenv()
    
    print("测试Server酱3推送...")
    result = send_message(
        title="测试推送 - 早晨提醒Agent",
        desp="这是一条测试消息\n\n来自早晨提醒Agent\n\n测试Markdown功能：\n- 列表1\n- 列表2",
        short="测试消息，请忽略",
        tags="测试"
    )
    print(f"结果: {result}")
