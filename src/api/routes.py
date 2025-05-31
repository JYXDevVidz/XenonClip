# src/api/routes.py
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import List, Optional
import logging
import os

from core.database import DatabaseManager
from core.ai_classifier import AIClassifier
from core.clipboard_monitor import ClipboardMonitor
from api.models import *

logger = logging.getLogger(__name__)

def create_app(db_manager: DatabaseManager, ai_classifier: AIClassifier, 
               clipboard_monitor: ClipboardMonitor) -> FastAPI:
    
    app = FastAPI(title="XenonClip API", version="1.0.0")
    
    # 获取静态文件路径
    static_path = os.path.join(os.path.dirname(__file__), '..', 'static')
    app.mount("/static", StaticFiles(directory=static_path), name="static")
    @app.put("/api/items/{item_id}/user-category")
    async def user_update_category(item_id: int, request: dict):
        """用户手动更新分类"""
        try:
            category = request.get('category')
            if not category:
                raise HTTPException(status_code=400, detail="分类不能为空")

            db_manager.update_item_category(item_id, category)
            return {"success": True, "message": "分类已更新"}
        except Exception as e:
            logger.error(f"更新分类失败: {e}")
            raise HTTPException(status_code=500, detail="更新分类失败")
    @app.get("/")
    async def root():
        index_path = os.path.join(static_path, "index.html")
        return FileResponse(index_path)
    
    @app.get("/api/items")
    async def get_items(limit: int = 100, category: Optional[str] = None, 
                       search: Optional[str] = None):
        """获取剪贴板条目"""
        try:
            items = db_manager.get_clipboard_items(limit, category, search)
            return {"success": True, "data": items}
        except Exception as e:
            logger.error(f"获取条目失败: {e}")
            raise HTTPException(status_code=500, detail="获取条目失败")
    
    @app.post("/api/items/{item_id}/copy")
    async def copy_item(item_id: int):
        """复制条目到剪贴板"""
        try:
            items = db_manager.get_clipboard_items(limit=1000)
            item = next((item for item in items if item['id'] == item_id), None)
            
            if not item:
                raise HTTPException(status_code=404, detail="条目不存在")
            
            import pyperclip
            pyperclip.copy(item['content'])
            
            # 更新访问信息
            content_hash = item.get('content_hash')
            if content_hash:
                db_manager.update_content_access(content_hash)
            
            return {"success": True, "message": "已复制到剪贴板"}
        except Exception as e:
            logger.error(f"复制失败: {e}")
            raise HTTPException(status_code=500, detail="复制失败")
    
    @app.put("/api/items/{item_id}/category")
    async def update_category(item_id: int, request: dict):
        """更新条目分类"""
        try:
            category = request.get('category')
            if not category:
                raise HTTPException(status_code=400, detail="分类不能为空")
            
            db_manager.update_item_category(item_id, category)
            return {"success": True, "message": "分类已更新"}
        except Exception as e:
            logger.error(f"更新分类失败: {e}")
            raise HTTPException(status_code=500, detail="更新分类失败")
    
    @app.post("/api/items/{item_id}/favorite")
    async def toggle_favorite(item_id: int):
        """切换收藏状态"""
        try:
            new_status = db_manager.toggle_favorite(item_id)
            return {"success": True, "is_favorite": new_status}
        except Exception as e:
            logger.error(f"切换收藏失败: {e}")
            raise HTTPException(status_code=500, detail="切换收藏失败")
    
    @app.delete("/api/items/{item_id}")
    async def delete_item(item_id: int):
        """删除条目"""
        try:
            db_manager.delete_item(item_id)
            return {"success": True, "message": "条目已删除"}
        except Exception as e:
            logger.error(f"删除失败: {e}")
            raise HTTPException(status_code=500, detail="删除失败")
    
    @app.get("/api/categories")
    async def get_categories():
        """获取所有分类"""
        try:
            categories = db_manager.get_all_categories()
            return {"success": True, "data": categories}
        except Exception as e:
            logger.error(f"获取分类失败: {e}")
            raise HTTPException(status_code=500, detail="获取分类失败")
    
    @app.post("/api/categories")
    async def create_category(request: dict):
        """创建新分类"""
        try:
            name = request.get('name')
            if not name:
                raise HTTPException(status_code=400, detail="分类名称不能为空")
            
            db_manager.add_category_if_not_exists(name)
            return {"success": True, "message": "分类已创建"}
        except Exception as e:
            logger.error(f"创建分类失败: {e}")
            raise HTTPException(status_code=500, detail="创建分类失败")
    
    @app.get("/api/stats")
    async def get_stats():
        """获取统计信息"""
        try:
            stats = ai_classifier.get_classification_stats()
            return {"success": True, "data": stats}
        except Exception as e:
            logger.error(f"获取统计失败: {e}")
            raise HTTPException(status_code=500, detail="获取统计失败")
    
    @app.get("/api/settings")
    async def get_settings():
        """获取设置"""
        try:
            settings = {
                "auto_classify": db_manager.get_setting("auto_classify", True),
                "classify_schedule": db_manager.get_setting("classify_schedule", "immediate"),
                "classify_time": db_manager.get_setting("classify_time", "09:00"),
                "retention_days": db_manager.get_setting("retention_days", 30),
                "enable_sensitive_detection": db_manager.get_setting("enable_sensitive_detection", True)
            }
            return {"success": True, "data": settings}
        except Exception as e:
            logger.error(f"获取设置失败: {e}")
            raise HTTPException(status_code=500, detail="获取设置失败")
    
    @app.post("/api/settings")
    async def update_settings(request: dict):
        """更新设置"""
        try:
            for key, value in request.items():
                if value is not None:
                    db_manager.set_setting(key, value)
            
            # 更新剪贴板监听器设置
            if 'auto_classify' in request:
                clipboard_monitor.set_auto_classify(request['auto_classify'])
            
            return {"success": True, "message": "设置已更新"}
        except Exception as e:
            logger.error(f"更新设置失败: {e}")
            raise HTTPException(status_code=500, detail="更新设置失败")
    
    @app.post("/api/classify/manual")
    async def manual_classify():
        """手动分类入口点 - 现在仅返回成功，实际分类由前端完成"""
        return {"success": True, "message": "请选择要应用的分类"}
    
    async def run_manual_classification():
        """运行手动分类任务"""
        try:
            # 获取未分类的条目
            items = db_manager.get_clipboard_items(limit=1000)
            unclassified_items = [item for item in items if item['category'] == '未分类']
            
            for item in unclassified_items:
                if not item['is_sensitive']:
                    category, confidence = ai_classifier.classify_content(item['content'])
                    db_manager.update_item_category(item['id'], category)
            
            logger.info(f"手动分类完成，处理了 {len(unclassified_items)} 个条目")
        except Exception as e:
            logger.error(f"手动分类任务失败: {e}")
    
    return app