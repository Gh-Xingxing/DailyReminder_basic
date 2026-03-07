"""
和风天气API对接模块
文档: https://dev.qweather.com/docs/api/
"""
import os
import requests
import json
from datetime import datetime, date
from typing import Optional, Dict, Any

# API配置
QWEATHER_HOST = os.getenv('QWEATHER_HOST', 'devapi.qweather.com')
QWEATHER_KEY = os.getenv('QWEATHER_KEY', '')
BASE_URL = f'https://{QWEATHER_HOST}/v7'

# 城市代码（深圳默认）
DEFAULT_LOCATION = os.getenv('USER_LOCATION', '101280601')


class WeatherAPI:
    """和风天气API封装"""
    
    def __init__(self, api_key: str = None, location: str = None, api_host: str = None):
        self.api_key = api_key or QWEATHER_KEY
        self.location = location or DEFAULT_LOCATION
        self.api_host = api_host or QWEATHER_HOST
        self.base_url = f'https://{self.api_host}/v7'
        
        if not self.api_key:
            raise ValueError("请设置和风天气API密钥 (QWEATHER_KEY)")
    
    def _request(self, endpoint: str, params: dict = None) -> Dict[str, Any]:
        """发送API请求"""
        url = f"{self.base_url}/{endpoint}"
        
        default_params = {
            'key': self.api_key,
            'location': self.location
        }
        
        if params:
            default_params.update(params)
        
        try:
            response = requests.get(url, params=default_params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') != '200':
                raise Exception(f"API错误: {data.get('code')} - {data.get('message', '未知错误')}")
            
            return data
        
        except requests.exceptions.Timeout:
            raise Exception("API请求超时")
        except requests.exceptions.RequestException as e:
            raise Exception(f"API请求失败: {str(e)}")
    
    def get_now(self) -> Dict[str, Any]:
        """获取实时天气"""
        data = self._request('weather/now')
        now = data.get('now', {})
        
        return {
            'temp': float(now.get('temp', 0)),  # 当前温度
            'feels_like': float(now.get('feelsLike', 0)),  # 体感温度
            'text': now.get('text', ''),  # 天气状况文字
            'icon': now.get('icon', ''),  # 天气图标代码
            'humidity': int(now.get('humidity', 0)),  # 湿度百分比
            'wind_dir': now.get('windDir', ''),  # 风向
            'wind_scale': now.get('windScale', ''),  # 风力等级
            'wind_speed': float(now.get('windSpeed', 0)),  # 风速 km/h
            'pressure': float(now.get('pressure', 0)),  # 气压
            'visibility': float(now.get('vis', 0)),  # 能见度 km
            'update_time': data.get('updateTime', ''),  # 更新时间
        }
    
    def get_3d(self) -> list:
        """获取3天天气预报"""
        data = self._request('weather/3d')
        daily = data.get('daily', [])
        
        result = []
        for day in daily:
            result.append({
                'date': day.get('fxDate', ''),  # 预报日期
                'temp_max': float(day.get('tempMax', 0)),  # 最高温度
                'temp_min': float(day.get('tempMin', 0)),  # 最低温度
                'text_day': day.get('textDay', ''),  # 白天天气
                'text_night': day.get('textNight', ''),  # 夜间天气
                'icon_day': day.get('iconDay', ''),
                'icon_night': day.get('iconNight', ''),
                'humidity': int(day.get('humidity', 0)),
                'wind_dir_day': day.get('windDirDay', ''),
                'wind_scale_day': day.get('windScaleDay', ''),
                'precipitation': float(day.get('precip', 0)),  # 降水量 mm
                'uv_index': day.get('uvIndex', ''),  # 紫外线指数
            })
        
        return result
    
    def get_today(self) -> Dict[str, Any]:
        """获取今日天气（结合实时和预报）"""
        now = self.get_now()
        forecast = self.get_3d()
        
        today_forecast = None
        if forecast:
            today_forecast = forecast[0]
        
        return {
            'current': now,
            'forecast': today_forecast,
            'date': date.today().isoformat(),
        }
    
    def get_warning(self) -> list:
        """获取天气预警"""
        try:
            data = self._request('warning/now')
            return data.get('warning', [])
        except Exception:
            return []  # 预警接口可能不可用，静默失败


# 便捷函数
def get_weather(location: str = None) -> Dict[str, Any]:
    """获取天气信息"""
    api = WeatherAPI(location=location)
    return api.get_today()


if __name__ == '__main__':
    # 测试
    import dotenv
    dotenv.load_dotenv()
    
    print("测试天气API...")
    try:
        weather = get_weather()
        print(f"当前温度: {weather['current']['temp']}C")
        print(f"天气状况: {weather['current']['text']}")
        print(f"湿度: {weather['current']['humidity']}%")
        
        if weather['forecast']:
            print(f"今日温度范围: {weather['forecast']['temp_min']}C - {weather['forecast']['temp_max']}C")
    except Exception as e:
        print(f"错误: {e}")
