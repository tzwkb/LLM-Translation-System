#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
"""

import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class DirectoryConfig:
    """目录配置"""
    root: str
    input: str
    output: str
    terminology: str
    cache: str
    
    @classmethod
    def create_default(cls, root_dir: str = ".") -> "DirectoryConfig":
        """创建默认目录配置"""
        return cls(
            root=root_dir,
            input=os.path.join(root_dir, "input"),
            output=os.path.join(root_dir, "output"),
            terminology=os.path.join(root_dir, "terminology"),
            cache=os.path.join(root_dir, "cache")
        )
    
    def ensure_directories(self):
        """确保所有目录存在"""
        for dir_path in [self.input, self.output, self.terminology, self.cache]:
            os.makedirs(dir_path, exist_ok=True)

@dataclass
class TranslationConfig:
    """翻译配置"""
    api_key: str = 'urapikey'
    base_url: str = 'ururl'
    model: str = 'gpt-4o'
    batch_size: int = 10
    delay: float = 1.0
    max_retries: int = 3
    auto_save_interval: int = 5

@dataclass
class AppConfig:
    """应用配置"""
    directories: DirectoryConfig
    translation: TranslationConfig
    verbose: bool = False
    
    @classmethod
    def create_default(cls, root_dir: str = ".") -> "AppConfig":
        """创建默认应用配置"""
        return cls(
            directories=DirectoryConfig.create_default(root_dir),
            translation=TranslationConfig(),
            verbose=False
        )
    
    def setup(self):
        """初始化配置"""
        self.directories.ensure_directories()
