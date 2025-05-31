# src/core/database.py
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import threading

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = "xenon_clip.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._initialize_database()
    
    def _initialize_database(self):
        """初始化数据库"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                # 剪贴板条目表
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS clipboard_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        content TEXT NOT NULL,
                        content_hash VARCHAR(64) UNIQUE NOT NULL,
                        category VARCHAR(50) DEFAULT '未分类',
                        confidence REAL DEFAULT 0.0,
                        is_sensitive BOOLEAN DEFAULT FALSE,
                        is_favorite BOOLEAN DEFAULT FALSE,
                        source_app VARCHAR(100),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        access_count INTEGER DEFAULT 1,
                        last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 分类表
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS categories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(50) UNIQUE NOT NULL,
                        color VARCHAR(7) DEFAULT '#1890ff',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 设置表
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS settings (
                        key VARCHAR(100) PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建索引
                conn.execute('CREATE INDEX IF NOT EXISTS idx_content_hash ON clipboard_items(content_hash)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_category ON clipboard_items(category)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON clipboard_items(created_at)')
                
                conn.commit()
                logger.info("数据库初始化完成")
                
            except Exception as e:
                logger.error(f"数据库初始化失败: {e}")
                conn.rollback()
            finally:
                conn.close()
    
    def add_clipboard_item(self, item: Dict[str, Any]) -> int:
        """添加剪贴板条目"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.execute('''
                    INSERT INTO clipboard_items 
                    (content, content_hash, category, confidence, is_sensitive, source_app)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    item['content'],
                    item['content_hash'],
                    item['category'],
                    item['confidence'],
                    item['is_sensitive'],
                    item['source_app']
                ))
                
                conn.commit()
                return cursor.lastrowid
                
            except Exception as e:
                logger.error(f"添加剪贴板条目失败: {e}")
                conn.rollback()
                return 0
            finally:
                conn.close()
    
    def content_exists(self, content_hash: str) -> bool:
        """检查内容是否已存在"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.execute(
                    'SELECT 1 FROM clipboard_items WHERE content_hash = ?',
                    (content_hash,)
                )
                return cursor.fetchone() is not None
            finally:
                conn.close()
    
    def update_content_access(self, content_hash: str):
        """更新内容访问信息"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute('''
                    UPDATE clipboard_items 
                    SET access_count = access_count + 1,
                        last_accessed = CURRENT_TIMESTAMP
                    WHERE content_hash = ?
                ''', (content_hash,))
                conn.commit()
            except Exception as e:
                logger.error(f"更新访问信息失败: {e}")
            finally:
                conn.close()
    
    def get_clipboard_items(self, limit: int = 100, category: str = None, 
                          search: str = None) -> List[Dict]:
        """获取剪贴板条目"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                query = '''
                    SELECT id, content, category, confidence, is_sensitive, 
                           is_favorite, source_app, created_at, access_count, last_accessed
                    FROM clipboard_items
                    WHERE 1=1
                '''
                params = []
                
                if category:
                    query += ' AND category = ?'
                    params.append(category)
                
                if search:
                    query += ' AND (content LIKE ? OR category LIKE ?)'
                    search_param = f'%{search}%'
                    params.extend([search_param, search_param])
                
                query += ' ORDER BY last_accessed DESC LIMIT ?'
                params.append(limit)
                
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
                
            except Exception as e:
                logger.error(f"获取剪贴板条目失败: {e}")
                return []
            finally:
                conn.close()
    
    def update_item_category(self, item_id: int, category: str):
        """更新条目分类"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute(
                    'UPDATE clipboard_items SET category = ? WHERE id = ?',
                    (category, item_id)
                )
                conn.commit()
            except Exception as e:
                logger.error(f"更新条目分类失败: {e}")
            finally:
                conn.close()
    
    def toggle_favorite(self, item_id: int) -> bool:
        """切换收藏状态"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                # 获取当前状态
                cursor = conn.execute(
                    'SELECT is_favorite FROM clipboard_items WHERE id = ?',
                    (item_id,)
                )
                row = cursor.fetchone()
                if not row:
                    return False
                
                new_status = not bool(row[0])
                conn.execute(
                    'UPDATE clipboard_items SET is_favorite = ? WHERE id = ?',
                    (new_status, item_id)
                )
                conn.commit()
                return new_status
            except Exception as e:
                logger.error(f"切换收藏状态失败: {e}")
                return False
            finally:
                conn.close()
    
    def delete_item(self, item_id: int):
        """删除条目"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute('DELETE FROM clipboard_items WHERE id = ?', (item_id,))
                conn.commit()
            except Exception as e:
                logger.error(f"删除条目失败: {e}")
            finally:
                conn.close()
    
    def cleanup_old_items(self, days: int = 30):
        """清理旧条目"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cutoff_date = datetime.now() - timedelta(days=days)
                conn.execute('''
                    DELETE FROM clipboard_items 
                    WHERE created_at < ? AND is_favorite = FALSE
                ''', (cutoff_date,))
                conn.commit()
            except Exception as e:
                logger.error(f"清理旧条目失败: {e}")
            finally:
                conn.close()
    
    def add_category_if_not_exists(self, category_name: str):
        """添加分类（如果不存在）"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute('''
                    INSERT OR IGNORE INTO categories (name) VALUES (?)
                ''', (category_name,))
                conn.commit()
            except Exception as e:
                logger.error(f"添加分类失败: {e}")
            finally:
                conn.close()
    
    def get_all_categories(self) -> List[Dict]:
        """获取所有分类"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                cursor = conn.execute('''
                    SELECT c.*, COUNT(ci.id) as item_count
                    FROM categories c
                    LEFT JOIN clipboard_items ci ON c.name = ci.category
                    GROUP BY c.id, c.name
                    ORDER BY c.name
                ''')
                return [dict(row) for row in cursor.fetchall()]
            except Exception as e:
                logger.error(f"获取分类失败: {e}")
                return []
            finally:
                conn.close()
    
    def get_classification_stats(self) -> Dict:
        """获取分类统计"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.execute('''
                    SELECT category, COUNT(*) as count, AVG(confidence) as avg_confidence
                    FROM clipboard_items
                    GROUP BY category
                    ORDER BY count DESC
                ''')
                
                stats = {}
                for row in cursor.fetchall():
                    stats[row[0]] = {
                        'count': row[1],
                        'avg_confidence': round(row[2] or 0, 2)
                    }
                
                return stats
            except Exception as e:
                logger.error(f"获取分类统计失败: {e}")
                return {}
            finally:
                conn.close()
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """获取设置"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.execute('SELECT value FROM settings WHERE key = ?', (key,))
                row = cursor.fetchone()
                if row:
                    try:
                        return json.loads(row[0])
                    except:
                        return row[0]
                return default
            except Exception as e:
                logger.error(f"获取设置失败: {e}")
                return default
            finally:
                conn.close()
    
    def set_setting(self, key: str, value: Any):
        """设置配置"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                value_str = json.dumps(value) if not isinstance(value, str) else value
                conn.execute('''
                    INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)
                ''', (key, value_str))
                conn.commit()
            except Exception as e:
                logger.error(f"设置配置失败: {e}")
            finally:
                conn.close()