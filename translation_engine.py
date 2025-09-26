#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
翻译引擎模块
"""

import time
import pandas as pd
from openai import OpenAI
from typing import Dict, List, Tuple, Optional, Any
from config_manager import TranslationConfig
import re

class TranslationEngine:
    """翻译引擎"""
    
    def __init__(self, config: TranslationConfig):
        self.config = config
        self.client = OpenAI(api_key=config.api_key, base_url=config.base_url)
    
    def translate_text(self, text: str, source_lang: str = "zh", target_lang: str = "en") -> str:
        """翻译单个文本"""
        for attempt in range(self.config.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=[{
                        "role": "user", 
                        "content": f"请将以下{source_lang}文本翻译成{target_lang}，只返回译文，不要解释：\n{text}"
                    }],
                    temperature=0.3
                )
                
                result = self._extract_response_content(response)
                if result and not self._is_html_response(result):
                    return result
                    
            except Exception as e:
                if attempt == self.config.max_retries - 1:
                    raise e
                time.sleep(self.config.delay * (attempt + 1))
        
        return f"[翻译失败: 超过最大重试次数]"
    
    def _extract_response_content(self, response) -> str:
        """提取API响应内容"""
        if hasattr(response, 'choices') and response.choices:
            return response.choices[0].message.content.strip()
        elif isinstance(response, str):
            return response.strip()
        elif isinstance(response, dict):
            if 'choices' in response and response['choices']:
                return response['choices'][0]['message']['content'].strip()
            elif 'content' in response:
                return response['content'].strip()
        return str(response)
    
    def _is_html_response(self, text: str) -> bool:
        """检查是否为HTML响应"""
        return text.lower().startswith(('<!doctype html>', '<html'))
    
    def is_fully_translated(self, text: str, source_lang: str) -> bool:
        """检查文本是否已完全翻译"""
        if source_lang == "zh":
            return not bool(re.search(r'[\u4e00-\u9fff]', text))
        return False

class TerminologyEngine:
    """术语引擎"""
    
    def __init__(self, terminology_file: Optional[str] = None, cache_dir: str = "cache"):
        self.terminology_dict = {}
        self.reverse_dict = {}
        self.replacement_cache = {}
        self.sorted_terms_cache = {}
        self.cache_dir = cache_dir
        
        if terminology_file:
            self.load_terminology(terminology_file)
    
    def load_terminology(self, file_path: str):
        """加载术语库（优化版本）"""
        import os
        import pickle
        import hashlib
        
        # 生成缓存文件路径
        file_hash = hashlib.md5(file_path.encode()).hexdigest()[:8]
        cache_file = os.path.join(self.cache_dir, f"terminology_{file_hash}.pkl")
        
        # 检查缓存
        if os.path.exists(cache_file):
            try:
                cache_mtime = os.path.getmtime(cache_file)
                file_mtime = os.path.getmtime(file_path)
                if cache_mtime > file_mtime:
                    with open(cache_file, 'rb') as f:
                        cached_data = pickle.load(f)
                        self.terminology_dict = cached_data['terminology_dict']
                        self.reverse_dict = cached_data['reverse_dict']
                        self.sorted_terms_cache = cached_data['sorted_terms_cache']
                    return
            except (OSError, pickle.PickleError):
                pass
        
        # 加载术语库
        df = pd.read_excel(file_path)
        if df.shape[1] < 2:
            raise ValueError("术语库文件至少需要两列")
        
        chinese_col, english_col = df.columns[0], df.columns[1]
        
        # 批量处理
        valid_mask = (
            df[chinese_col].notna() & df[english_col].notna() &
            (df[chinese_col] != '') & (df[english_col] != '') &
            (df[chinese_col] != 'nan') & (df[english_col] != 'nan')
        )
        
        valid_df = df[valid_mask]
        self.terminology_dict = dict(zip(
            valid_df[chinese_col].astype(str).str.strip(),
            valid_df[english_col].astype(str).str.strip()
        ))
        
        self.reverse_dict = {v: k for k, v in self.terminology_dict.items()}
        
        # 预计算排序缓存
        self._update_sorted_cache()
        
        # 保存缓存
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            with open(cache_file, 'wb') as f:
                pickle.dump({
                    'terminology_dict': self.terminology_dict,
                    'reverse_dict': self.reverse_dict,
                    'sorted_terms_cache': self.sorted_terms_cache
                }, f)
        except (OSError, pickle.PickleError):
            pass
    
    def _update_sorted_cache(self):
        """更新排序缓存"""
        for direction in ['zh_to_en', 'en_to_zh']:
            source_dict = self.terminology_dict if direction == 'zh_to_en' else self.reverse_dict
            self.sorted_terms_cache[direction] = sorted(
                source_dict.keys(), key=len, reverse=True
            )
    
    def replace_terms_in_text(self, text: str, source_lang: str, target_lang: str) -> Tuple[str, List[str]]:
        """替换文本中的术语（优化版本）"""
        if not self.terminology_dict:
            return text, []
        
        # 使用缓存
        cache_key = (text, source_lang, target_lang)
        if cache_key in self.replacement_cache:
            return self.replacement_cache[cache_key]
        
        # 确定替换方向
        direction = 'zh_to_en' if source_lang == 'zh' and target_lang == 'en' else 'en_to_zh'
        source_dict = self.terminology_dict if direction == 'zh_to_en' else self.reverse_dict
        
        if direction not in self.sorted_terms_cache:
            self._update_sorted_cache()
        
        replaced_terms = []
        result_text = text
        
        # 按长度排序替换（避免短词优先匹配）
        for term in self.sorted_terms_cache[direction]:
            if term in source_dict:
                target_term = source_dict[term]
                # 使用词边界匹配
                pattern = r'\b' + re.escape(term) + r'\b'
                if re.search(pattern, result_text):
                    result_text = re.sub(pattern, target_term, result_text)
                    replaced_terms.append(f"{term} -> {target_term}")
        
        # 缓存结果
        result = (result_text, replaced_terms)
        self.replacement_cache[cache_key] = result
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """获取术语库统计信息"""
        return {
            "total_terms": len(self.terminology_dict),
            "chinese_to_english": len(self.terminology_dict),
            "english_to_chinese": len(self.reverse_dict),
            "cache_hits": len(self.replacement_cache),
            "sorted_cache": len(self.sorted_terms_cache)
        }

class ProcessingVisualizer:
    """处理过程可视化器（简化版）"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.step_counter = 0
    
    def show_step(self, step_name: str, content: str = "", details: str = ""):
        """显示处理步骤"""
        if not self.verbose:
            return
        self.step_counter += 1
        print(f"\n{'='*50}")
        print(f"📝 步骤 {self.step_counter}: {step_name}")
        if content:
            print(f"📄 {content}")
        if details:
            print(f"🔍 {details}")
    
    def show_terminology_replacement(self, original: str, processed: str, terms: List[str]):
        """显示术语替换"""
        if not self.verbose or not terms:
            return
        print(f"\n🔄 术语替换 ({len(terms)} 个):")
        for term in terms[:3]:  # 只显示前3个
            print(f"  • {term}")
        if len(terms) > 3:
            print(f"  ... 还有 {len(terms) - 3} 个")
    
    def show_sentence_summary(self, idx: int, original: str, final: str, elapsed_time: float, term_count: int):
        """显示句子处理总结"""
        if not self.verbose:
            return
        print(f"\n📋 处理完成 [行{idx}] - {elapsed_time:.2f}s")
        if term_count > 0:
            print(f"   术语替换: {term_count} 个")
        print(f"   原文: {original[:30]}{'...' if len(original) > 30 else ''}")
        print(f"   译文: {final[:30]}{'...' if len(final) > 30 else ''}")
    
    def reset_counter(self):
        """重置计数器"""
        self.step_counter = 0
