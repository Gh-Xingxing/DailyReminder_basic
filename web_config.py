#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置网页 - 每日提醒助手
功能：开学日期设置、课表导入、每日提醒配置、测试推送
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
import json
import sys
from datetime import datetime
from werkzeug.utils import secure_filename

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入课表解析模块
from import_courses import parse_excel

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['SECRET_KEY'] = 'morning-reminder-config-2026'

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 配置文件路径
CONFIG_FILE = 'config.json'

DEFAULT_READING_REMINDER = "📚 每天复习今日重点"
DEFAULT_PROJECT_REMINDER = "📝 提前整理明日待办事项"


def load_config():
    """加载主配置"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "user": {"name": "", "location": "101110101", "location_name": "请填写你的城市名称"},
            "semester": {"start_date": "", "total_weeks": 16, "current_week": None},
            "reminder": {
                "time": "23:30",
                "skip_weekend": True,
                "daily_reading_reminder": True,
                "project_idea_reminder": True,
                "items": [DEFAULT_READING_REMINDER, DEFAULT_PROJECT_REMINDER]
            },
            "courses": []
        }


def save_config(config):
    """保存主配置"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_reminder_items(config):
    reminder = config.get('reminder', {})
    items = reminder.get('items')
    if isinstance(items, list):
        normalized_items = [str(item).strip() for item in items if str(item).strip()]
        if normalized_items:
            return normalized_items

    fallback_items = []
    if reminder.get('daily_reading_reminder', False):
        fallback_items.append(DEFAULT_READING_REMINDER)
    if reminder.get('project_idea_reminder', False):
        fallback_items.append(DEFAULT_PROJECT_REMINDER)
    return fallback_items


def update_reminder_config(config, skip_weekend, raw_items):
    reminder = config.setdefault('reminder', {})
    items = [line.strip() for line in raw_items.splitlines() if line.strip()]

    reminder['skip_weekend'] = bool(skip_weekend)
    reminder['items'] = items
    reminder['daily_reading_reminder'] = DEFAULT_READING_REMINDER in items
    reminder['project_idea_reminder'] = DEFAULT_PROJECT_REMINDER in items
    return items


def calculate_current_week(start_date_str):
    """计算当前周次"""
    if not start_date_str:
        return None
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        today = datetime.now()
        delta = today - start_date
        current_week = (delta.days // 7) + 1
        return current_week if current_week > 0 else None
    except ValueError:
        return None


@app.route('/')
def index():
    """配置页面首页"""
    config = load_config()
    
    semester = config.get('semester', {})
    start_date = semester.get('start_date', '')
    total_weeks = semester.get('total_weeks', 16)
    current_week = calculate_current_week(start_date)
    
    return render_template('index.html',
        config=config,
        start_date=start_date,
        total_weeks=total_weeks,
        current_week=current_week,
        courses_count=len(config.get('courses', [])),
        reminder_items='\n'.join(get_reminder_items(config))
    )


@app.route('/api/semester', methods=['POST'])
def save_semester():
    """保存学期配置"""
    data = request.json
    config = load_config()
    
    if 'semester' not in config:
        config['semester'] = {}
    
    config['semester']['start_date'] = data.get('start_date', '')
    config['semester']['total_weeks'] = int(data.get('total_weeks', 16))
    
    # 计算当前周次
    current_week = calculate_current_week(config['semester']['start_date'])
    config['semester']['current_week'] = current_week
    
    save_config(config)
    
    return jsonify({
        'success': True,
        'current_week': current_week,
        'message': f'学期配置已保存，当前第{current_week}周' if current_week else '学期配置已保存'
    })


@app.route('/api/upload-courses', methods=['POST'])
def upload_courses():
    """上传并导入课表"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '没有选择文件'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': '没有选择文件'})
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'success': False, 'error': '只支持 Excel 文件 (.xlsx, .xls)'})
    
    try:
        # 保存文件
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # 解析课表
        result = parse_excel(filepath)
        
        if not result['success']:
            return jsonify({'success': False, 'error': result.get('message', '解析失败')})
        
        # 更新配置
        config = load_config()
        config['courses'] = result['courses']
        save_config(config)
        
        return jsonify({
            'success': True,
            'message': result['message'],
            'courses_count': len(result['courses'])
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'导入失败: {str(e)}'})


@app.route('/api/courses', methods=['GET'])
def get_courses():
    """获取课程列表"""
    config = load_config()
    courses = config.get('courses', [])
    
    # 按星期分组
    grouped = {}
    weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    
    for course in courses:
        weekday = course.get('weekday', 1)
        if weekday not in grouped:
            grouped[weekday] = {'name': weekday_names[weekday - 1], 'courses': []}
        grouped[weekday]['courses'].append(course)
    
    # 排序
    sorted_courses = []
    for i in range(1, 8):
        if i in grouped:
            sorted_courses.append(grouped[i])
    
    return jsonify({
        'success': True,
        'courses': courses,
        'grouped': sorted_courses,
        'total': len(courses)
    })


@app.route('/api/courses/clear', methods=['POST'])
def clear_courses():
    """清空课程列表"""
    config = load_config()
    config['courses'] = []
    save_config(config)
    return jsonify({'success': True, 'message': '课程列表已清空'})



@app.route('/api/courses/add', methods=['POST'])
def add_course():
    """添加单个课程"""
    data = request.json
    config = load_config()
    
    # 验证必填字段
    required = ['course_name', 'weekday', 'start_section', 'end_section', 'start_week', 'end_week']
    for field in required:
        if field not in data:
            return jsonify({'success': False, 'error': f'缺少必填字段: {field}'})
    
    # 构建课程对象
    course = {
        'course_name': data['course_name'],
        'teacher': data.get('teacher', ''),
        'location': data.get('location', ''),
        'weekday': int(data['weekday']),
        'start_section': int(data['start_section']),
        'end_section': int(data['end_section']),
        'week_type': data.get('week_type', 'all'),
        'start_week': int(data['start_week']),
        'end_week': int(data['end_week'])
    }
    
    config['courses'].append(course)
    save_config(config)
    
    return jsonify({
        'success': True,
        'message': f'课程 "{course["course_name"]}" 已添加',
        'course': course
    })


@app.route('/api/courses/edit', methods=['POST'])
def edit_course():
    """编辑单个课程"""
    data = request.json
    config = load_config()
    
    # 需要课程索引来定位
    index = data.get('index')
    if index is None:
        return jsonify({'success': False, 'error': '缺少课程索引'})
    
    courses = config.get('courses', [])
    if index < 0 or index >= len(courses):
        return jsonify({'success': False, 'error': '课程索引无效'})
    
    # 更新课程信息
    course = courses[index]
    if 'course_name' in data:
        course['course_name'] = data['course_name']
    if 'teacher' in data:
        course['teacher'] = data['teacher']
    if 'location' in data:
        course['location'] = data['location']
    if 'weekday' in data:
        course['weekday'] = int(data['weekday'])
    if 'start_section' in data:
        course['start_section'] = int(data['start_section'])
    if 'end_section' in data:
        course['end_section'] = int(data['end_section'])
    if 'week_type' in data:
        course['week_type'] = data['week_type']
    if 'start_week' in data:
        course['start_week'] = int(data['start_week'])
    if 'end_week' in data:
        course['end_week'] = int(data['end_week'])
    
    save_config(config)
    
    return jsonify({
        'success': True,
        'message': f'课程 "{course["course_name"]}" 已更新',
        'course': course
    })


@app.route('/api/courses/delete', methods=['POST'])
def delete_course():
    """删除单个课程"""
    data = request.json
    config = load_config()
    
    index = data.get('index')
    if index is None:
        return jsonify({'success': False, 'error': '缺少课程索引'})
    
    courses = config.get('courses', [])
    if index < 0 or index >= len(courses):
        return jsonify({'success': False, 'error': '课程索引无效'})
    
    deleted_course = courses.pop(index)
    save_config(config)
    
    return jsonify({
        'success': True,
        'message': f'课程 "{deleted_course["course_name"]}" 已删除'
    })


@app.route('/api/location', methods=['GET', 'POST'])
def handle_location():
    """获取或设置天气城市"""
    config = load_config()
    
    if request.method == 'GET':
        user = config.get('user', {})
        return jsonify({
            'success': True,
            'location': user.get('location', '101110101'),
            'location_name': user.get('location_name', '请填写你的城市名称')
        })
    
    # POST - 保存
    data = request.json
    if 'user' not in config:
        config['user'] = {}
    
    config['user']['location'] = data.get('location', '101110101')
    config['user']['location_name'] = data.get('location_name', '请填写你的城市名称')
    save_config(config)
    
    return jsonify({
        'success': True,
        'message': f'城市已设置为 {data.get("location_name", "")}'
    })


@app.route('/api/reminder', methods=['POST'])
def save_reminder():
    data = request.json or {}
    config = load_config()
    skip_weekend = data.get('skip_weekend', True)
    items = update_reminder_config(config, skip_weekend, data.get('items', ''))
    save_config(config)

    return jsonify({
        'success': True,
        'message': f'每日提醒设置已保存，共 {len(items)} 条提醒',
        'items_count': len(items)
    })


@app.route('/api/test-push', methods=['POST'])
def test_push():
    """测试推送"""
    try:
        from push import ServerChanPush
        push = ServerChanPush()
        result = push.send(
            "【测试推送】每日提醒助手",
            "这是一条测试消息，配置网页推送功能正常！\n\n如果您收到此消息，说明推送配置正确。"
        )
        
        if result['success']:
            return jsonify({'success': True, 'message': '测试推送已发送，请检查微信是否收到消息'})
        else:
            return jsonify({'success': False, 'error': result.get('error', '推送失败')})
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'推送失败: {str(e)}'})


@app.route('/api/test-run', methods=['POST'])
def test_run():
    """测试运行主程序"""
    try:
        # 导入主程序并运行
        import main as main_module
        
        # 调用主函数
        main_module.main()
        
        return jsonify({'success': True, 'message': '主程序已执行，请检查微信是否收到推送'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'执行失败: {str(e)}'})


if __name__ == '__main__':
    print("=" * 50)
    print("每日提醒助手 - 配置网页")
    print("=" * 50)
    print(f"访问地址: http://localhost:5000")
    print("按 Ctrl+C 停止服务")
    print("=" * 50)
    app.run(debug=False, host='127.0.0.1', port=5000, use_reloader=False)
