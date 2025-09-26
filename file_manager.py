#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件管理器模块
"""

import os
import glob
from typing import List, Optional, Tuple
from config_manager import DirectoryConfig

class FileManager:
    """文件管理器"""
    
    def __init__(self, config: DirectoryConfig):
        self.config = config
    
    def find_input_files(self) -> List[str]:
        """查找输入文件"""
        patterns = ['*.xlsx', '*.xls']
        files = []
        for pattern in patterns:
            files.extend(glob.glob(os.path.join(self.config.input, pattern)))
        return sorted(files, key=os.path.getmtime, reverse=True)
    
    def find_terminology_files(self) -> List[str]:
        """查找术语库文件"""
        patterns = ['*.xlsx', '*.xls']
        files = []
        for pattern in patterns:
            files.extend(glob.glob(os.path.join(self.config.terminology, pattern)))
        return sorted(files, key=os.path.getmtime, reverse=True)
    
    def generate_output_path(self, input_file: str, suffix: str = "_translated") -> str:
        """生成输出文件路径"""
        filename = os.path.basename(input_file)
        name, ext = os.path.splitext(filename)
        output_filename = f"{name}{suffix}{ext}"
        return os.path.join(self.config.output, output_filename)
    
    def generate_cache_path(self, input_file: str, cache_type: str) -> str:
        """生成缓存文件路径"""
        filename = os.path.basename(input_file)
        name, _ = os.path.splitext(filename)
        cache_filename = f"{name}_{cache_type}.pkl"
        return os.path.join(self.config.cache, cache_filename)
    
    def get_relative_path(self, file_path: str) -> str:
        """获取相对路径（用于显示）"""
        try:
            return os.path.relpath(file_path, self.config.root)
        except ValueError:
            return file_path
    
    def validate_input_file(self, file_path: str) -> bool:
        """验证输入文件"""
        if not os.path.exists(file_path):
            return False
        if not file_path.lower().endswith(('.xlsx', '.xls')):
            return False
        return True
    
    def cleanup_cache(self, max_age_days: int = 7):
        """清理过期缓存文件"""
        import time
        current_time = time.time()
        cache_files = glob.glob(os.path.join(self.config.cache, "*.pkl"))
        
        cleaned = 0
        for cache_file in cache_files:
            file_age = current_time - os.path.getmtime(cache_file)
            if file_age > max_age_days * 24 * 3600:  # 转换为秒
                try:
                    os.remove(cache_file)
                    cleaned += 1
                except OSError:
                    pass
        
        return cleaned

class FileSelector:
    """文件选择器"""
    
    def __init__(self, file_manager: FileManager):
        self.file_manager = file_manager
    
    def select_input_file(self) -> Optional[str]:
        """交互式选择输入文件"""
        files = self.file_manager.find_input_files()
        
        if not files:
            print(f"❌ 在 {self.file_manager.config.input} 目录中未找到Excel文件")
            print("请将待翻译的Excel文件放入 input/ 目录")
            return None
        
        print(f"\n📁 在 input/ 目录中找到 {len(files)} 个Excel文件:")
        for i, file_path in enumerate(files, 1):
            filename = os.path.basename(file_path)
            size = os.path.getsize(file_path) / 1024  # KB
            mtime = os.path.getmtime(file_path)
            from datetime import datetime
            time_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
            print(f"  {i}. {filename} ({size:.1f}KB, {time_str})")
            if i >= 10:  # 限制显示数量
                print(f"  ... 还有 {len(files) - 10} 个文件")
                break
        
        while True:
            choice = input(f"\n选择输入文件编号 (1-{min(len(files), 10)}): ").strip()
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < min(len(files), 10):
                    return files[idx]
            print("❌ 请输入有效的文件编号")
    
    def select_terminology_file(self) -> Optional[str]:
        """交互式选择术语库文件"""
        files = self.file_manager.find_terminology_files()
        
        if not files:
            print(f"📚 在 terminology/ 目录中未找到术语库文件")
            return None
        
        print(f"\n📚 在 terminology/ 目录中找到 {len(files)} 个术语库文件:")
        for i, file_path in enumerate(files, 1):
            filename = os.path.basename(file_path)
            size = os.path.getsize(file_path) / 1024  # KB
            print(f"  {i}. {filename} ({size:.1f}KB)")
            if i >= 5:  # 限制显示数量
                break
        
        choice = input(f"选择术语库编号 (1-{min(len(files), 5)}, 留空跳过): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= min(len(files), 5):
            return files[int(choice) - 1]
        return None
