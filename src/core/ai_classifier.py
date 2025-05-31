# src/core/ai_classifier.py
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from .ollama_manager import OllamaManager
from .database import DatabaseManager

logger = logging.getLogger(__name__)

class AIClassifier:
    def __init__(self, ollama_manager: OllamaManager, db_manager: DatabaseManager):
        self.ollama = ollama_manager
        self.db = db_manager
        
        # 预设分类
        self.default_categories = [
            "文本内容",      # 普通文本、笔记、想法
            "网址链接",      # URL、链接
            "代码片段",      # 代码、配置文件
            "数字信息",      # 电话、身份证、账号等
            "邮箱地址",      # 邮箱
            "密码凭据",      # 密码、token、密钥（敏感）
            "图片路径",      # 文件路径、图片路径
            "办公文档",      # 工作相关文档内容
            "购物信息",      # 商品信息、价格、购物相关
            "日程安排"       # 时间、日期、计划
        ]
        
        self._initialize_categories()
    
    def _initialize_categories(self):
        """初始化默认分类"""
        for category in self.default_categories:
            self.db.add_category_if_not_exists(category)
    
    def classify_content(self, content: str) -> Tuple[str, float]:
        """
        分类剪贴板内容
        返回: (分类名称, 置信度)
        """
        # 获取当前所有分类
        categories = self.db.get_all_categories()
        category_list = [cat['name'] for cat in categories]
        
        # 构建分类提示
        prompt = self._build_classification_prompt(content, category_list)
        
        # 调用AI模型
        response = self.ollama.generate_response(prompt)
        
        if not response:
            return "文本内容", 0.5  # 默认分类
        
        # 解析响应
        category, confidence = self._parse_classification_response(response, category_list)
        
        # 如果是新分类建议，则创建新分类
        if category.startswith("NEW_CATEGORY:"):
            new_category = category.replace("NEW_CATEGORY:", "").strip()
            if new_category and len(new_category) <= 20:  # 限制分类名长度
                self.db.add_category_if_not_exists(new_category)
                logger.info(f"创建新分类: {new_category}")
                return new_category, confidence
            else:
                return "文本内容", 0.5
        
        return category, confidence
    
    def _build_classification_prompt(self, content: str, categories: List[str]) -> str:
        """构建分类提示词"""
        # 限制内容长度，避免token超限
        if len(content) > 500:
            content = content[:500] + "..."
        
        categories_str = "\n".join([f"{i+1}. {cat}" for i, cat in enumerate(categories)])
        
        prompt = f"""请对以下内容进行分类。

可选分类：
{categories_str}

待分类内容：
{content}

请按以下格式回复：
如果属于现有分类，回复：分类名称|置信度(0.0-1.0)
如果需要新分类，回复：NEW_CATEGORY:新分类名称|置信度(0.0-1.0)

示例：
代码片段|0.9
或
NEW_CATEGORY:学习笔记|0.8

请只回复分类结果，不要解释："""

        return prompt
    
    def _parse_classification_response(self, response: str, categories: List[str]) -> Tuple[str, float]:
        """解析AI响应"""
        try:
            # 清理响应
            response = response.strip()
            
            # 按|分割
            if '|' in response:
                parts = response.split('|')
                category = parts[0].strip()
                try:
                    confidence = float(parts[1].strip())
                    confidence = max(0.0, min(1.0, confidence))  # 限制在0-1之间
                except:
                    confidence = 0.5
            else:
                category = response.strip()
                confidence = 0.5
            
            # 验证分类是否存在（除非是新分类）
            if not category.startswith("NEW_CATEGORY:"):
                if category not in categories:
                    # 尝试模糊匹配
                    category = self._fuzzy_match_category(category, categories)
            
            return category, confidence
            
        except Exception as e:
            logger.error(f"解析分类响应失败: {e}, 响应: {response}")
            return "文本内容", 0.5
    
    def _fuzzy_match_category(self, input_category: str, categories: List[str]) -> str:
        """模糊匹配分类"""
        input_lower = input_category.lower()
        
        # 精确匹配
        for cat in categories:
            if cat.lower() == input_lower:
                return cat
        
        # 包含匹配
        for cat in categories:
            if input_lower in cat.lower() or cat.lower() in input_lower:
                return cat
        
        # 关键词匹配
        keyword_mapping = {
            "url": "网址链接",
            "link": "网址链接", 
            "code": "代码片段",
            "email": "邮箱地址",
            "mail": "邮箱地址",
            "password": "密码凭据",
            "pwd": "密码凭据",
            "number": "数字信息",
            "phone": "数字信息",
            "file": "图片路径",
            "path": "图片路径"
        }
        
        for keyword, category in keyword_mapping.items():
            if keyword in input_lower and category in categories:
                return category
        
        return "文本内容"  # 默认分类
    
    def get_classification_stats(self) -> Dict:
        """获取分类统计信息"""
        return self.db.get_classification_stats()