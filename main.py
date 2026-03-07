#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
主程序 - 早晨提醒Agent（基础版）
功能：
1. 读取配置
2. 获取明日天气
3. 获取明日课程（支持周次和单双周筛选）
4. 组装并推送消息
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta, timezone
import pytz
import logging

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # GitHub Actions 使用 Secrets，不需要 .env 文件

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入自定义模块
from weather_api import WeatherAPI
from push import ServerChanPush

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 默认值
DEFAULT_MOTIVATION = "每一天都是新的开始，保持热爱，奔赴山海。"

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')


def get_beijing_now():
    """获取北京时间（无论服务器在哪个时区）"""
    return datetime.now(BEIJING_TZ)


def load_config():
    """加载配置文件"""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("配置文件 config.json 未找到")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"配置文件格式错误: {e}")
        raise


def calculate_current_week(config):
    """计算当前是第几周（使用北京时间）"""
    semester = config.get('semester', {})
    start_date_str = semester.get('start_date')
    
    if not start_date_str:
        return None
    
    try:
        # 开学日期设为北京时间
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        start_date = BEIJING_TZ.localize(start_date)
        
        # 获取当前北京时间
        now = get_beijing_now()
        
        # 计算周次
        delta = now - start_date
        current_week = (delta.days // 7) + 1
        total_weeks = semester.get('total_weeks', 16)
        
        logger.info(f"北京时间: {now.strftime('%Y-%m-%d %H:%M:%S')}, 距开学 {delta.days} 天")
        
        if current_week < 1:
            return None  # 还没开学
        if current_week > total_weeks:
            return total_weeks  # 已超过总周数
        
        return current_week
    except ValueError:
        logger.error(f"开学日期格式错误: {start_date_str}")
        return None


def get_tomorrow_weather(config):
    """获取明日天气信息"""
    try:
        location = config['user']['location']
        weather_api = WeatherAPI(location=location)
        
        # 获取3天预报
        forecast_3d = weather_api.get_3d()
        today_forecast = forecast_3d[0] if len(forecast_3d) > 0 else None
        tomorrow_forecast = forecast_3d[1] if len(forecast_3d) > 1 else None
        
        # 获取24小时预报
        hourly_data = []
        try:
            hourly_data = weather_api._request('weather/24h').get('hourly', [])
        except Exception as e:
            logger.warning(f"获取24小时预报失败: {e}")
        
        if not tomorrow_forecast:
            logger.warning("无法获取明日天气预报")
            return None
            
        # 解析今天天气信息（用于对比）
        today_info = None
        if today_forecast:
            today_info = {
                'temp_max': today_forecast['temp_max'],
                'temp_min': today_forecast['temp_min'],
                'text_day': today_forecast['text_day'],
                'text_night': today_forecast['text_night']
            }
        
        # 解析明天天气信息
        weather_info = {
            'temp_max': tomorrow_forecast['temp_max'],
            'temp_min': tomorrow_forecast['temp_min'],
            'text_day': tomorrow_forecast['text_day'],
            'text_night': tomorrow_forecast['text_night'],
            'has_rain_snow': '雨' in tomorrow_forecast['text_day'] or '雪' in tomorrow_forecast['text_day'] or 
                             '雨' in tomorrow_forecast['text_night'] or '雪' in tomorrow_forecast['text_night'],
            'today_info': today_info
        }
        
        # 计算特定时间温度
        temp_730 = None
        temps_am = []
        temps_pm = []
        
        # 获取北京时间明天
        beijing_now = get_beijing_now()
        beijing_tomorrow = beijing_now.date() + timedelta(days=1)
        
        for hour_data in hourly_data:
            try:
                # 解析时间
                fx_time = datetime.fromisoformat(hour_data['fxTime'].replace('Z', '+00:00'))
                beijing_time = fx_time.astimezone(BEIJING_TZ)  # 转换为北京时间
                
                # 检查是否为明天（北京时间）
                if beijing_time.date() != beijing_tomorrow:
                    continue
                    
                temp = float(hour_data['temp'])
                
                # 7:30温度（取7点数据）
                if beijing_time.hour == 7:
                    temp_730 = temp
                
                # 上午温度（7-11点）
                if 7 <= beijing_time.hour <= 11:
                    temps_am.append(temp)
                
                # 下午温度（12-18点）
                if 12 <= beijing_time.hour <= 18:
                    temps_pm.append(temp)
                    
            except (ValueError, KeyError):
                continue
        
        # 设置温度值
        weather_info['temp_730'] = temp_730 if temp_730 is not None else (weather_info['temp_max'] + weather_info['temp_min']) / 2
        weather_info['temp_am_avg'] = sum(temps_am) / len(temps_am) if temps_am else (weather_info['temp_max'] + weather_info['temp_min']) / 2
        weather_info['temp_pm_avg'] = sum(temps_pm) / len(temps_pm) if temps_pm else (weather_info['temp_max'] + weather_info['temp_min']) / 2
        
        return weather_info
    except Exception as e:
        logger.error(f"获取天气信息失败: {e}")
        return None


def get_tomorrow_courses(config, current_week):
    """获取明日课程（支持周次和单双周筛选）"""
    try:
        courses = config.get('courses', [])
        if not courses:
            return [], []
            
        # 计算明天是星期几（使用北京时间）
        beijing_now = get_beijing_now()
        tomorrow_weekday = (beijing_now.weekday() + 1) % 7 + 1  # 明天的星期几 (1-7)
        # weekday(): 0=周一, 6=周日
        # 明天 = (今天 + 1) % 7，然后 +1 转换为 1-7
        if beijing_now.weekday() == 6:  # 今天是周日
            tomorrow_weekday = 1  # 明天是周一
        else:
            tomorrow_weekday = beijing_now.weekday() + 2  # 周一(0) -> 周二(2)
        
        logger.info(f"北京时间今天星期{beijing_now.weekday() + 1}，明天星期{tomorrow_weekday}")
        
        # 筛选明天的课程
        tomorrow_courses = []
        for course in courses:
            if course.get('weekday') != tomorrow_weekday:
                continue
            
            # 如果有周次信息，进行周次筛选
            if current_week is not None:
                start_week = course.get('start_week', 1)
                end_week = course.get('end_week', 16)
                week_type = course.get('week_type', 'all')
                
                # 检查是否在周次范围内
                if not (start_week <= current_week <= end_week):
                    continue
                
                # 检查单双周
                if week_type == 'odd' and current_week % 2 == 0:
                    continue
                if week_type == 'even' and current_week % 2 == 1:
                    continue
            
            tomorrow_courses.append(course)
        
        # 按上午/下午分组
        morning_courses = [course for course in tomorrow_courses if 1 <= course.get('start_section', 0) <= 4]
        afternoon_courses = [course for course in tomorrow_courses if 5 <= course.get('start_section', 0) <= 8]
        
        # 按节次排序
        morning_courses.sort(key=lambda x: x.get('start_section', 0))
        afternoon_courses.sort(key=lambda x: x.get('start_section', 0))
        
        return morning_courses, afternoon_courses
    except Exception as e:
        logger.error(f"获取课程信息失败: {e}")
        return [], []


def assemble_message(config, weather_info, morning_courses, afternoon_courses, current_week):
    """组装消息"""
    try:
        # 标题
        course_count = len(morning_courses) + len(afternoon_courses)
        weather_summary = f"{weather_info['temp_min']}C~{weather_info['temp_max']}C" if weather_info else "未知"
        week_info = f"第{current_week}周" if current_week else ""
        title = f"{week_info} | {weather_summary} | {course_count}节课"
        
        # 正文
        lines = []
        
        # 课程部分
        lines.append("## 明日课程")
        
        if morning_courses:
            lines.append("**上午**：")
            for course in morning_courses:
                teacher = course.get('teacher', '')
                teacher_info = f" {teacher}" if teacher else ""
                lines.append(f"- {course['course_name']}（第{course['start_section']}-{course['end_section']}节）{course['location']}{teacher_info}")
        else:
            lines.append("**上午**：无课程")
        
        lines.append("")  # 空行
        
        if afternoon_courses:
            lines.append("**下午**：")
            for course in afternoon_courses:
                teacher = course.get('teacher', '')
                teacher_info = f" {teacher}" if teacher else ""
                lines.append(f"- {course['course_name']}（第{course['start_section']}-{course['end_section']}节）{course['location']}{teacher_info}")
        else:
            lines.append("**下午**：无课程")
        
        lines.append("")  # 空行
        
        # 天气部分
        lines.append("## 明日天气")
        if weather_info:
            lines.append(f"- 温度：{weather_info['temp_min']}C ~ {weather_info['temp_max']}C")
            lines.append(f"- 早7:30：{weather_info['temp_730']:.0f}C")
            lines.append(f"- 上午平均：{weather_info['temp_am_avg']:.0f}C")
            lines.append(f"- 下午平均：{weather_info['temp_pm_avg']:.0f}C")
            
            weather_desc = f"{weather_info['text_day']}"
            if weather_info['has_rain_snow']:
                weather_desc += "，有雨雪"
            else:
                weather_desc += "，无雨雪"
            lines.append(f"- 天气：{weather_desc}")
        else:
            lines.append("- 无法获取天气信息")
        
        lines.append("")  # 空行
        
        # 每日提醒部分（从配置读取）
        reminder_config = config.get('reminder', {})
        reminder_items = reminder_config.get('items', [])
        if reminder_items:
            lines.append("## 每日提醒")
            for item in reminder_items:
                lines.append(f"- {item}")
            lines.append("")  # 空行
        
        # 激励话语
        lines.append("## 今日激励")
        lines.append(DEFAULT_MOTIVATION)
        
        return title, '\n'.join(lines)
    except Exception as e:
        logger.error(f"组装消息失败: {e}")
        return "提醒消息", "无法生成完整消息内容"


def send_notification(title, content):
    """发送推送通知"""
    try:
        push = ServerChanPush()
        result = push.send(title, content)
        if result['success']:
            logger.info("消息推送成功")
        else:
            logger.error(f"消息推送失败: {result['error']}")
        return result['success']
    except Exception as e:
        logger.error(f"推送消息时发生错误: {e}")
        return False


def main():
    """主函数"""
    try:
        # 1. 读取配置
        logger.info("正在读取配置文件...")
        config = load_config()
        
        # 2. 计算当前周次
        current_week = calculate_current_week(config)
        if current_week:
            logger.info(f"当前是第 {current_week} 周")
        else:
            logger.info("未设置开学日期或尚未开学，跳过周次筛选")
        
        # 3. 获取明日天气
        logger.info("正在获取明日天气...")
        weather_info = get_tomorrow_weather(config)
        
        # 4. 获取明日课程
        logger.info("正在获取明日课程...")
        morning_courses, afternoon_courses = get_tomorrow_courses(config, current_week)
        
        # 5. 组装消息
        logger.info("正在组装消息...")
        title, content = assemble_message(config, weather_info, morning_courses, afternoon_courses, current_week)
        
        # 6. 推送消息
        logger.info("正在推送消息...")
        success = send_notification(title, content)
        
        if success:
            logger.info("主程序执行成功")
        else:
            logger.warning("主程序执行完成，但消息推送失败")
            
    except Exception as e:
        logger.error(f"主程序执行出错: {e}")
        # 即使出错也尝试发送错误通知
        send_notification("提醒Agent执行出错", f"执行过程中发生错误：{str(e)}")


if __name__ == "__main__":
    main()
