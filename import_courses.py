#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
课表导入工具 - 适配教务系统导出的矩阵式课表

使用方法：
    python import_courses.py 学生课表.xlsx

课表格式说明：
    - 矩阵式课表：行=节次，列=星期
    - 每个单元格可能包含多门课程，或同一课程的不同周次安排
    
    格式示例1（同一课程不同周次不同节次）：
        计算机网络组建与设计实训[000000001] 04
        16周 5-6节 张三[22222222,副教授] 一教1513
        计算机科学与技术2404班
        计算机网络组建与设计实训[000000001] 04
        9-15周 5-8节 张三[22222222,副教授] 一教1513
    
    格式示例2（同一课程不同周次不同地点）：
        计算机网络[000000004] 04
        1-8周 3-4节 王五[21111262,讲师] 一教1227
        9-16周 3-4节 王五[21111262,讲师] 一教1517
"""

import os
import sys
import json
import re
import pandas as pd
from typing import List, Dict, Any

# 节次映射：行索引 -> (开始节, 结束节)
SECTION_MAPPING = {
    2: (1, 2), 3: (1, 2),
    4: (3, 4), 5: (3, 4),
    6: (5, 6), 7: (5, 6),
    8: (7, 8), 9: (7, 8),
    10: (9, 10), 11: (9, 10),
}

# 星期映射
WEEKDAY_MAPPING = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7}


def parse_arrangements(text: str) -> List[Dict[str, Any]]:
    """
    解析课程安排信息
    
    支持格式：
    - 16周 5-6节 教师[编码,职称] 地点
    - 9-15周 5-8节 教师[编码,职称] 地点
    - 1-8周(双) 3-4节 教师[编码,职称] 地点
    """
    results = []
    
    # 正则：支持单周(16周)和多周(9-15周)，支持单双周
    pattern = r'(\d+)(?:-(\d+))?周(?:\((单|双)\))?\s+(\d+)-(\d+)节\s+([^\[\s]+)\[(\d+),([^\]]+)\]\s+(\S+)'
    
    for match in re.finditer(pattern, text):
        start_week = int(match.group(1))
        end_week = int(match.group(2)) if match.group(2) else start_week
        week_type_str = match.group(3)
        start_section = int(match.group(4))
        end_section = int(match.group(5))
        teacher_name = match.group(6).strip()
        location = match.group(9).strip()
        
        # 清理地点
        if '班' in location:
            location = re.sub(r'[\u4e00-\u9fa5]+\d*班.*', '', location).strip()
        
        week_type = 'all'
        if week_type_str == '单':
            week_type = 'odd'
        elif week_type_str == '双':
            week_type = 'even'
        
        results.append({
            'start_week': start_week,
            'end_week': end_week,
            'week_type': week_type,
            'start_section': start_section,
            'end_section': end_section,
            'teacher': teacher_name,
            'location': location
        })
    
    return results


def parse_course_cell(cell_content: str, weekday: int, default_start: int, default_end: int) -> List[Dict[str, Any]]:
    """解析单元格中的课程"""
    if not cell_content or pd.isna(cell_content):
        return []
    
    content = str(cell_content)
    courses = []
    
    # 找到所有课程名（格式：课程名[编码] 数字，位于行首或换行后）
    course_pattern = r'(?:^|\n)([^\[\n]+)\[(\d+)\]\s*(\d+)\s*\n'
    course_matches = list(re.finditer(course_pattern, content, re.MULTILINE))
    
    if not course_matches:
        return []
    
    for i, match in enumerate(course_matches):
        course_name = match.group(1).strip()
        
        # 获取该课程块的内容
        if i + 1 < len(course_matches):
            block = content[match.start():course_matches[i + 1].start()]
        else:
            block = content[match.start():]
        
        # 解析安排信息
        arrangements = parse_arrangements(block)
        
        if arrangements:
            for arr in arrangements:
                courses.append({
                    'course_name': course_name,
                    'teacher': arr['teacher'],
                    'location': arr['location'],
                    'weekday': weekday,
                    'start_section': arr['start_section'],
                    'end_section': arr['end_section'],
                    'week_type': arr['week_type'],
                    'start_week': arr['start_week'],
                    'end_week': arr['end_week']
                })
        else:
            # 备用解析
            courses.append(parse_fallback(block, course_name, weekday, default_start, default_end))
    
    return courses

    # 找到所有课程名（格式：课程名[编码] 数字）
    course_pattern = r'([^\[]+)\[(\d+)\]\s*(\d+)'
    course_matches = list(re.finditer(course_pattern, content))
    
    if not course_matches:
        return []
    
    for i, match in enumerate(course_matches):
        course_name = match.group(1).strip()
        
        # 获取该课程块的内容
        if i + 1 < len(course_matches):
            block = content[match.start():course_matches[i + 1].start()]
        else:
            block = content[match.start():]
        
        # 解析安排信息
        arrangements = parse_arrangements(block)
        
        if arrangements:
            for arr in arrangements:
                courses.append({
                    'course_name': course_name,
                    'teacher': arr['teacher'],
                    'location': arr['location'],
                    'weekday': weekday,
                    'start_section': arr['start_section'],
                    'end_section': arr['end_section'],
                    'week_type': arr['week_type'],
                    'start_week': arr['start_week'],
                    'end_week': arr['end_week']
                })
        else:
            # 备用解析
            courses.append(parse_fallback(block, course_name, weekday, default_start, default_end))
    
    return courses


def parse_fallback(content: str, course_name: str, weekday: int, default_start: int, default_end: int) -> Dict[str, Any]:
    """备用解析方法"""
    # 周次
    week_match = re.search(r'(\d+)-(\d+)周(?:\((单|双)\))?', content)
    start_week, end_week, week_type = 1, 16, 'all'
    if week_match:
        start_week = int(week_match.group(1))
        end_week = int(week_match.group(2))
        if week_match.group(3) == '单':
            week_type = 'odd'
        elif week_match.group(3) == '双':
            week_type = 'even'
    
    # 节次
    section_match = re.search(r'(\d+)-(\d+)节', content)
    start_section = section_match and int(section_match.group(1)) or default_start
    end_section = section_match and int(section_match.group(2)) or default_end
    
    # 教师
    teacher_match = re.search(r'([^\[\s]+)\[(\d+),([^\]]+)\]', content)
    teacher = teacher_match and teacher_match.group(1).strip() or ""
    
    # 地点
    location = ""
    if teacher_match:
        after = content[teacher_match.end():].strip()
        loc_match = re.match(r'(一教\d+|科研楼\d+|[^\s]+训练场|[^\s]+场)', after)
        if loc_match:
            location = loc_match.group(1)
    
    return {
        'course_name': course_name,
        'teacher': teacher,
        'location': location,
        'weekday': weekday,
        'start_section': start_section,
        'end_section': end_section,
        'week_type': week_type,
        'start_week': start_week,
        'end_week': end_week
    }


def parse_excel(file_path: str) -> Dict[str, Any]:
    """解析Excel课表"""
    result = {'success': False, 'message': '', 'courses': [], 'errors': []}
    
    try:
        df = pd.read_excel(file_path, header=None)
        all_courses = []
        
        for row_idx in range(2, len(df)):
            if row_idx not in SECTION_MAPPING:
                continue
            start_section, end_section = SECTION_MAPPING[row_idx]
            
            for col_idx in range(1, len(df.columns)):
                if col_idx not in WEEKDAY_MAPPING:
                    continue
                
                weekday = WEEKDAY_MAPPING[col_idx]
                cell = df.iloc[row_idx, col_idx]
                courses = parse_course_cell(cell, weekday, start_section, end_section)
                all_courses.extend(courses)
        
        # 去重
        seen = set()
        unique_courses = []
        for c in all_courses:
            key = (c['course_name'], c['weekday'], c['start_section'], c['end_section'],
                   c['week_type'], c['start_week'], c['end_week'], c['location'])
            if key not in seen:
                seen.add(key)
                unique_courses.append(c)
        
        unique_courses.sort(key=lambda x: (x['weekday'], x['start_section'], x['start_week']))
        
        result['courses'] = unique_courses
        result['success'] = True
        result['message'] = f'成功解析 {len(unique_courses)} 门课程'
        
    except Exception as e:
        result['errors'].append(f'文件读取失败: {str(e)}')
        result['message'] = 'Excel文件读取失败'
    
    return result


def update_config(courses: list) -> bool:
    """更新config.json"""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        config['courses'] = courses
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"错误: 更新配置失败: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("使用方法: python import_courses.py <课表Excel文件>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"错误: 文件不存在: {file_path}")
        sys.exit(1)
    
    print(f"正在解析: {file_path}\n")
    
    result = parse_excel(file_path)
    
    if result['errors']:
        print("解析错误:")
        for e in result['errors']:
            print(f"  - {e}")
    
    if not result['success']:
        print(f"\n解析失败: {result['message']}")
        sys.exit(1)
    
    print(f"{result['message']}\n")
    
    # 显示结果
    weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    for weekday in range(1, 8):
        day_courses = [c for c in result['courses'] if c['weekday'] == weekday]
        if day_courses:
            print(f"【{weekday_names[weekday - 1]}】")
            for c in day_courses:
                week_info = f"{c['start_week']}-{c['end_week']}周"
                if c['week_type'] == 'odd':
                    week_info += "(单)"
                elif c['week_type'] == 'even':
                    week_info += "(双)"
                print(f"  第{c['start_section']}-{c['end_section']}节 | {c['course_name']} | {c['teacher']} | {c['location']} | {week_info}")
            print()
    
    if update_config(result['courses']):
        print(f"[OK] 已更新 config.json，共导入 {len(result['courses'])} 门课程")
    else:
        print("[ERROR] 更新配置失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
