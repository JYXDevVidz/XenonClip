# src/core/ollama_manager.py
import subprocess
import sys
import time
import requests
import json
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class OllamaManager:
    def __init__(self):
        self.model_name = "qwen3:0.6b"  # 使用更小的模型
        self.ollama_url = "http://localhost:11434"
        
    def check_ollama_installed(self) -> bool:
        """检查Ollama是否已安装"""
        try:
            result = subprocess.run(['ollama', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def install_ollama(self) -> bool:
        """使用winget安装Ollama"""
        try:
            logger.info("正在安装Ollama...")
            result = subprocess.run([
                'winget', 'install', '--id', 'Ollama.Ollama', '--silent'
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info("Ollama安装成功")
                return True
            else:
                logger.error(f"Ollama安装失败: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"安装Ollama时发生错误: {e}")
            return False
    
    def start_ollama_service(self) -> bool:
        """启动Ollama服务"""
        try:
            # 检查服务是否已运行
            if self.check_ollama_running():
                return True
                
            # 启动服务
            subprocess.Popen(['ollama', 'serve'], 
                           creationflags=subprocess.CREATE_NO_WINDOW)
            
            # 等待服务启动
            for _ in range(30):  # 最多等待30秒
                time.sleep(1)
                if self.check_ollama_running():
                    return True
            
            return False
        except Exception as e:
            logger.error(f"启动Ollama服务失败: {e}")
            return False
    
    def check_ollama_running(self) -> bool:
        """检查Ollama服务是否运行"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def pull_model(self) -> bool:
        """拉取模型"""
        try:
            logger.info(f"正在拉取模型 {self.model_name}...")
            result = subprocess.run([
                'ollama', 'pull', self.model_name
            ], capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                logger.info("模型拉取成功")
                return True
            else:
                logger.error(f"模型拉取失败: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"拉取模型时发生错误: {e}")
            return False
    
    def check_model_exists(self) -> bool:
        """检查模型是否存在"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                return any(model['name'] == self.model_name for model in models)
            return False
        except:
            return False
    
    async def initialize(self) -> bool:
        """初始化Ollama环境"""
        # 1. 检查安装
        if not self.check_ollama_installed():
            if not self.install_ollama():
                return False
        
        # 2. 启动服务
        if not self.start_ollama_service():
            return False
        
        # 3. 检查模型
        if not self.check_model_exists():
            if not self.pull_model():
                return False
        
        logger.info("Ollama环境初始化完成")
        return True
    
    def generate_response(self, prompt: str) -> Optional[str]:
        """调用模型生成响应"""
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # 降低随机性，提高分类一致性
                    "top_p": 0.9,
                    "max_tokens": 100
                }
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                raw_response = result.get('response', '')
                
                # 移除思考内容
                cleaned_response = self._remove_thinking_tags(raw_response)
                return cleaned_response.strip()
            else:
                logger.error(f"模型调用失败: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"调用模型时发生错误: {e}")
            return None
    
    def _remove_thinking_tags(self, text: str) -> str:
        """移除思考标签内容"""
        import re
        # 移除 <think>...</think> 和可能的变体
        patterns = [
            r'<think>.*?</think>',
            r'<thinking>.*?</thinking>',
            r'<thought>.*?</thought>'
        ]
        
        for pattern in patterns:
            text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)
        
        return text