#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查点管理器模块
"""

import os
import pickle
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime

class CheckpointManager:
    """检查点管理器（简化版）"""
    
    def __init__(self, input_file: str, output_file: str, cache_dir: str = "cache"):
        self.input_file = input_file
        self.output_file = output_file
        self.cache_dir = cache_dir
        self.auto_save_interval = 5
        
        # 生成检查点文件名
        input_name = os.path.splitext(os.path.basename(input_file))[0]
        self.checkpoint_file = os.path.join(cache_dir, f"{input_name}_checkpoint.pkl")
        
        os.makedirs(cache_dir, exist_ok=True)
    
    def has_checkpoint(self) -> bool:
        """检查是否存在检查点"""
        return os.path.exists(self.checkpoint_file)
    
    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """加载检查点"""
        if not self.has_checkpoint():
            return None
        
        try:
            with open(self.checkpoint_file, 'rb') as f:
                checkpoint = pickle.load(f)
            
            # 验证检查点有效性
            if self._validate_checkpoint(checkpoint):
                return checkpoint
                
        except (OSError, pickle.PickleError, KeyError):
            pass
        
        return None
    
    def save_checkpoint(self, current_idx: int, total_rows: int, df: pd.DataFrame, 
                       completed: List[int], failed: List[int], stats: Dict[str, Any]):
        """保存检查点"""
        checkpoint = {
            'timestamp': datetime.now().isoformat(),
            'current_index': current_idx,
            'total_rows': total_rows,
            'completed_indices': completed,
            'failed_indices': failed,
            'statistics': stats,
            'dataframe': df.to_dict(),
            'input_file': self.input_file,
            'output_file': self.output_file
        }
        
        try:
            with open(self.checkpoint_file, 'wb') as f:
                pickle.dump(checkpoint, f)
        except (OSError, pickle.PickleError):
            pass
    
    def cleanup_checkpoint(self):
        """清理检查点文件"""
        if os.path.exists(self.checkpoint_file):
            try:
                os.remove(self.checkpoint_file)
            except OSError:
                pass
    
    def _validate_checkpoint(self, checkpoint: Dict[str, Any]) -> bool:
        """验证检查点有效性"""
        required_keys = ['current_index', 'total_rows', 'completed_indices', 'dataframe']
        return all(key in checkpoint for key in required_keys)
    
    def get_resume_info(self, checkpoint: Dict[str, Any]) -> str:
        """获取恢复信息"""
        completed = len(checkpoint.get('completed_indices', []))
        total = checkpoint.get('total_rows', 0)
        timestamp = checkpoint.get('timestamp', 'Unknown')
        
        return f"检查点时间: {timestamp}\n进度: {completed}/{total} ({completed/total*100:.1f}%)"
