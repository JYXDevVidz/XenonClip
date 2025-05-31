
# src/core/clipboard_monitor.py
import threading
import time
import hashlib
import logging
from datetime import datetime
from typing import Optional, Callable
import pyperclip
from core.database import DatabaseManager
from core.ai_classifier import AIClassifier

logger = logging.getLogger(__name__)

class ClipboardMonitor:
    def __init__(self, db_manager: DatabaseManager, ai_classifier: AIClassifier):
        self.db = db_manager
        self.ai_classifier = ai_classifier
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.last_content = ""
        self.last_hash = ""
        self.on_new_content: Optional[Callable] = None
        
        # 配置参数
        self.check_interval = 0.5  # 检查间隔（秒）
        self.auto_classify = True  # 是否自动分类
        
    def start(self):
        """开始监听剪贴板"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        logger.info("剪贴板监听已启动")
    
    def stop(self):
        """停止监听剪贴板"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("剪贴板监听已停止")
    
    def _monitor_loop(self):
        """监听循环"""
        while self.running:
            try:
                current_content = pyperclip.paste()
                
                if current_content and current_content != self.last_content:
                    # 计算内容哈希
                    content_hash = self._calculate_hash(current_content)
                    
                    # 避免重复记录相同内容
                    if content_hash != self.last_hash:
                        self._process_new_content(current_content, content_hash)
                        self.last_content = current_content
                        self.last_hash = content_hash
                
            except Exception as e:
                logger.error(f"剪贴板监听错误: {e}")
            
            time.sleep(self.check_interval)
    
    def _calculate_hash(self, content: str) -> str:
        """计算内容哈希"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _process_new_content(self, content: str, content_hash: str):
        """处理新的剪贴板内容"""
        try:
            # 检查是否已存在
            if self.db.content_exists(content_hash):
                # 更新访问时间和次数
                self.db.update_content_access(content_hash)
                return
            
            # 检测敏感内容
            is_sensitive = self._detect_sensitive_content(content)
            
            # AI分类
            category = "未分类"
            confidence = 0.0
            
            if self.auto_classify and not is_sensitive:
                try:
                    category, confidence = self.ai_classifier.classify_content(content)
                except Exception as e:
                    logger.error(f"AI分类失败: {e}")
            
            # 保存到数据库
            item_id = self.db.add_clipboard_item({
                'content': content,
                'content_hash': content_hash,
                'category': category,
                'confidence': confidence,
                'is_sensitive': is_sensitive,
                'source_app': self._get_active_app(),
                'created_at': datetime.now()
            })
            
            # 通知回调
            if self.on_new_content:
                self.on_new_content({
                    'id': item_id,
                    'content': content,
                    'category': category,
                    'is_sensitive': is_sensitive
                })
            
            logger.info(f"新剪贴板内容已保存: {category} (置信度: {confidence:.2f})")
            
        except Exception as e:
            logger.error(f"处理剪贴板内容失败: {e}")
    
    def _detect_sensitive_content(self, content: str) -> bool:
        return False
    
    def _get_active_app(self) -> str:
        """获取当前活动应用（简化实现）"""
        try:
            import psutil
            import win32gui
            import win32process
            
            # 获取前台窗口
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                process = psutil.Process(pid)
                return process.name()
        except:
            pass
        
        return "unknown"
    
    def set_auto_classify(self, enabled: bool):
        """设置是否自动分类"""
        self.auto_classify = enabled
    
    def set_callback(self, callback: Callable):
        """设置新内容回调"""
        self.on_new_content = callback