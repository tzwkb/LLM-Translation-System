#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLMTS 翻译工具 - 工程化版本
双语平行翻译工具，支持术语库、断点续传、详细处理过程展示
"""

import os
import sys
import time
import pandas as pd
from typing import Optional, List, Dict, Any
from tqdm import tqdm

# 导入自定义模块
from config_manager import AppConfig
from file_manager import FileManager, FileSelector
from translation_engine import TranslationEngine, TerminologyEngine, ProcessingVisualizer
from checkpoint_manager import CheckpointManager

class TranslationOrchestrator:
    """翻译协调器 - 核心业务逻辑"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.file_manager = FileManager(config.directories)
        self.file_selector = FileSelector(self.file_manager)
        self.translation_engine = TranslationEngine(config.translation)
        self.terminology_engine = None
        self.visualizer = ProcessingVisualizer(config.verbose)
        
    def setup_terminology(self, terminology_file: Optional[str]):
        """设置术语库"""
        if terminology_file and os.path.exists(terminology_file):
            self.terminology_engine = TerminologyEngine(
                terminology_file, 
                self.config.directories.cache
            )
            stats = self.terminology_engine.get_stats()
            print(f"✅ 术语库已加载: {stats['total_terms']} 条术语")
        else:
            self.terminology_engine = None
            print("⚠️ 未使用术语库")
    
    def detect_languages(self, df: pd.DataFrame) -> tuple:
        """检测源语言和目标语言"""
        columns = df.columns.tolist()
        
        # 简单的语言检测逻辑
        source_lang, target_lang = "zh", "en"
        source_col, target_col = columns[0], columns[1]
        
        # 根据列名推断语言
        if any(keyword in columns[0].lower() for keyword in ['chinese', 'zh', '中文']):
            source_lang, target_lang = "zh", "en"
            source_col, target_col = columns[0], columns[1]
        elif any(keyword in columns[0].lower() for keyword in ['english', 'en']):
            source_lang, target_lang = "en", "zh"
            source_col, target_col = columns[1], columns[0]
        
        return source_lang, target_lang, source_col, target_col
    
    def process_translation(self, input_file: str, output_file: str, terminology_file: Optional[str] = None) -> str:
        """处理翻译任务"""
        print(f"\n📂 输入文件: {self.file_manager.get_relative_path(input_file)}")
        print(f"📂 输出文件: {self.file_manager.get_relative_path(output_file)}")
        
        # 设置术语库
        self.setup_terminology(terminology_file)
        
        # 设置检查点管理器
        checkpoint_manager = CheckpointManager(
            input_file, output_file, self.config.directories.cache
        )
        
        # 检查是否有检查点
        checkpoint = None
        if checkpoint_manager.has_checkpoint():
            checkpoint_info = checkpoint_manager.get_resume_info(
                checkpoint_manager.load_checkpoint() or {}
            )
            print(f"\n🔄 发现检查点:")
            print(checkpoint_info)
            
            resume = input("是否从检查点继续? (y/n, 默认y): ").strip().lower()
            if resume != 'n':
                checkpoint = checkpoint_manager.load_checkpoint()
        
        # 加载数据
        if checkpoint:
            df = pd.DataFrame.from_dict(checkpoint['dataframe'])
            completed_indices = checkpoint['completed_indices']
            failed_indices = checkpoint.get('failed_indices', [])
            terminology_stats = checkpoint.get('statistics', {"total_replacements": 0})
            print(f"✅ 从检查点恢复，已完成 {len(completed_indices)} 行")
        else:
            df = pd.read_excel(input_file)
            completed_indices = []
            failed_indices = []
            terminology_stats = {"total_replacements": 0}
        
        # 验证数据格式
        if df.shape[1] < 2:
            raise ValueError("Excel文件至少需要两列（源语言和目标语言）")
        
        # 检测语言和列
        source_lang, target_lang, source_col, target_col = self.detect_languages(df)
        print(f"🌐 检测到语言: {source_lang} → {target_lang}")
        print(f"📋 列映射: '{source_col}' → '{target_col}'")
        
        # 确定需要翻译的行
        empty_mask = df[target_col].isna() | (df[target_col] == '') | (df[target_col] == 'nan')
        rows_to_translate = df.index[empty_mask].tolist()
        
        # 排除已完成的行
        rows_to_translate = [idx for idx in rows_to_translate if idx not in completed_indices]
        
        if not rows_to_translate:
            print("✅ 所有行都已翻译完成")
            return output_file
        
        print(f"📝 需要翻译: {len(rows_to_translate)} 行")
        
        # 开始翻译
        return self._execute_translation(
            df, rows_to_translate, source_lang, target_lang, 
            source_col, target_col, output_file,
            checkpoint_manager, completed_indices, failed_indices, terminology_stats
        )
    
    def _execute_translation(self, df: pd.DataFrame, rows_to_translate: List[int],
                           source_lang: str, target_lang: str, source_col: str, target_col: str,
                           output_file: str, checkpoint_manager: CheckpointManager,
                           completed_indices: List[int], failed_indices: List[int],
                           terminology_stats: Dict[str, Any]) -> str:
        """执行翻译过程"""
        
        total_rows = len(rows_to_translate)
        
        try:
            with tqdm(total=total_rows, desc="翻译进度", unit="行") as pbar:
                for i, idx in enumerate(rows_to_translate):
                    sentence_start_time = time.time()
                    self.visualizer.reset_counter()
                    
                    # 获取原文
                    source_text = str(df.loc[idx, source_col]).strip()
                    if not source_text:
                        completed_indices.append(idx)
                        pbar.update(1)
                        continue
                    
                    self.visualizer.show_step("读取原文", source_text, f"行号: {idx}")
                    
                    # 术语替换
                    processed_text = source_text
                    replaced_terms = []
                    
                    if self.terminology_engine:
                        processed_text, replaced_terms = self.terminology_engine.replace_terms_in_text(
                            source_text, source_lang, target_lang
                        )
                        
                        if replaced_terms:
                            terminology_stats["total_replacements"] += len(replaced_terms)
                            self.visualizer.show_terminology_replacement(
                                source_text, processed_text, replaced_terms
                            )
                            
                            # 简化显示
                            if not self.config.verbose:
                                print(f"术语替换 [{idx}]: {len(replaced_terms)} 个")
                    
                    # 翻译处理
                    try:
                        if (self.terminology_engine and 
                            self.translation_engine.is_fully_translated(processed_text, source_lang)):
                            translated_text = processed_text
                            if not self.config.verbose:
                                print(f"完全匹配 [{idx}]: 无需API翻译")
                        else:
                            translated_text = self.translation_engine.translate_text(
                                processed_text, source_lang, target_lang
                            )
                        
                        df.loc[idx, target_col] = translated_text
                        completed_indices.append(idx)
                        
                    except Exception as e:
                        error_msg = f"[翻译失败: {str(e)[:50]}]"
                        df.loc[idx, target_col] = error_msg
                        failed_indices.append(idx)
                        if not self.config.verbose:
                            print(f"❌ 翻译失败 [{idx}]: {str(e)[:100]}")
                    
                    # 显示处理总结
                    elapsed_time = time.time() - sentence_start_time
                    self.visualizer.show_sentence_summary(
                        idx, source_text, df.loc[idx, target_col], 
                        elapsed_time, len(replaced_terms)
                    )
                    
                    pbar.update(1)
                    
                    # 自动保存检查点
                    if (i + 1) % self.config.translation.auto_save_interval == 0:
                        checkpoint_manager.save_checkpoint(
                            idx, total_rows, df, completed_indices, failed_indices, terminology_stats
                        )
                        
                    # API调用延迟
                    if replaced_terms and len(replaced_terms) == 0:  # 只有API调用时才延迟
                        time.sleep(self.config.translation.delay)
        
        except KeyboardInterrupt:
            print("\n⚠️ 翻译被中断，正在保存进度...")
            checkpoint_manager.save_checkpoint(
                rows_to_translate[i] if i < len(rows_to_translate) else -1,
                total_rows, df, completed_indices, failed_indices, terminology_stats
            )
            print("💾 进度已保存，下次可以继续翻译")
            return output_file
        
        # 保存结果
        df.to_excel(output_file, index=False)
        
        # 清理检查点
        checkpoint_manager.cleanup_checkpoint()
        
        # 显示统计信息
        self._show_final_stats(completed_indices, failed_indices, terminology_stats)
        
        return output_file
    
    def _show_final_stats(self, completed: List[int], failed: List[int], terminology_stats: Dict[str, Any]):
        """显示最终统计信息"""
        print(f"\n{'='*50}")
        print("📊 翻译完成统计:")
        print(f"  ✅ 成功翻译: {len(completed)} 行")
        print(f"  ❌ 翻译失败: {len(failed)} 行")
        print(f"  🔄 术语替换: {terminology_stats.get('total_replacements', 0)} 次")
        
        if self.terminology_engine:
            stats = self.terminology_engine.get_stats()
            print(f"  📚 术语库: {stats['total_terms']} 条术语")
        
        print(f"{'='*50}")

def main():
    """主函数"""
    print("🎯 LLMTS 翻译工具 - 工程化版本")
    print("="*50)
    
    # 初始化配置
    config = AppConfig.create_default()
    config.setup()
    
    # 创建翻译协调器
    orchestrator = TranslationOrchestrator(config)
    
    # 清理过期缓存
    cleaned = orchestrator.file_manager.cleanup_cache()
    if cleaned > 0:
        print(f"🗑️ 清理了 {cleaned} 个过期缓存文件")
    
    # 选择输入文件
    input_file = orchestrator.file_selector.select_input_file()
    if not input_file:
        return
    
    # 生成输出文件路径
    output_file = orchestrator.file_manager.generate_output_path(input_file)
    print(f"📁 输出路径: {orchestrator.file_manager.get_relative_path(output_file)}")
    
    # 选择术语库
    terminology_file = orchestrator.file_selector.select_terminology_file()
    if terminology_file:
        print(f"📚 术语库: {orchestrator.file_manager.get_relative_path(terminology_file)}")
    
    # 询问是否启用详细模式
    verbose_choice = input("是否启用详细处理过程显示? (y/n, 默认n): ").strip().lower()
    config.verbose = (verbose_choice == 'y')
    orchestrator.visualizer.verbose = config.verbose
    
    if config.verbose:
        print("✅ 已启用详细模式")
    
    # 开始翻译
    print("\n" + "="*50)
    print("🚀 开始翻译...")
    
    try:
        result_file = orchestrator.process_translation(input_file, output_file, terminology_file)
        print(f"\n🎉 翻译完成!")
        print(f"📂 结果文件: {orchestrator.file_manager.get_relative_path(result_file)}")
        
    except Exception as e:
        print(f"\n❌ 翻译过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
