# main.py (根目录)
import asyncio
import logging
import sys
import webbrowser
import threading
import time
from pathlib import Path
import os

import uvicorn
from pystray import Icon, MenuItem, Menu
from PIL import Image
import keyboard

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.database import DatabaseManager
from core.ollama_manager import OllamaManager
from core.ai_classifier import AIClassifier
from core.clipboard_monitor import ClipboardMonitor
from api.routes import create_app

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class XenonClipApp:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.ollama_manager = OllamaManager()
        self.ai_classifier = None
        self.clipboard_monitor = None
        self.app = None
        self.server = None
        self.tray_icon = None
        self.port = 8000
        
    async def initialize(self):
        """初始化应用"""
        try:
            logger.info("正在初始化XenonClip...")
            
            # 初始化Ollama环境
            if not await self.ollama_manager.initialize():
                logger.error("Ollama初始化失败")
                return False
            
            # 初始化AI分类器
            self.ai_classifier = AIClassifier(self.ollama_manager, self.db_manager)
            
            # 初始化剪贴板监听器
            self.clipboard_monitor = ClipboardMonitor(self.db_manager, self.ai_classifier)
            
            # 创建FastAPI应用
            self.app = create_app(self.db_manager, self.ai_classifier, self.clipboard_monitor)
            
            logger.info("XenonClip初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"初始化失败: {e}")
            return False
    
    def start_server(self):
        """启动服务器"""
        try:
            config = uvicorn.Config(
                self.app,
                host="127.0.0.1",
                port=self.port,
                log_level="error"  # 减少日志输出
            )
            self.server = uvicorn.Server(config)
            
            # 在新线程中运行服务器
            server_thread = threading.Thread(target=self.server.run, daemon=True)
            server_thread.start()
            
            # 等待服务器启动
            time.sleep(2)
            logger.info(f"服务器已启动: http://127.0.0.1:{self.port}")
            
        except Exception as e:
            logger.error(f"启动服务器失败: {e}")
    
    def start_clipboard_monitor(self):
        """启动剪贴板监听"""
        try:
            self.clipboard_monitor.start()
            logger.info("剪贴板监听已启动")
        except Exception as e:
            logger.error(f"启动剪贴板监听失败: {e}")
    
    def setup_hotkeys(self):
        """设置全局热键"""
        try:
            # Ctrl+Shift+V 打开剪贴板管理器
            keyboard.add_hotkey('ctrl+shift+v', self.show_window)
            logger.info("全局热键已设置: Ctrl+Shift+V")
        except Exception as e:
            logger.error(f"设置热键失败: {e}")
    
    def show_window(self):
        """显示窗口"""
        try:
            webbrowser.open(f"http://127.0.0.1:{self.port}")
        except Exception as e:
            logger.error(f"打开窗口失败: {e}")
    
    def create_tray_icon(self):
        """创建系统托盘图标"""
        try:
            # 创建简单的图标（实际项目中应该使用图片文件）
            image = Image.new('RGB', (64, 64), color='blue')
            
            menu = Menu(
                MenuItem("打开剪贴板", self.show_window),
                MenuItem("设置", lambda: webbrowser.open(f"http://127.0.0.1:{self.port}#settings")),
                Menu.SEPARATOR,
                MenuItem("退出", self.quit_app)
            )
            
            self.tray_icon = Icon("XenonClip", image, "XenonClip - AI剪贴板管理器", menu)
            
            # 在新线程中运行托盘图标
            tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
            tray_thread.start()
            
            logger.info("系统托盘图标已创建")
            
        except Exception as e:
            logger.error(f"创建系统托盘失败: {e}")
    
    def quit_app(self, icon=None, item=None):
        """退出应用"""
        try:
            logger.info("正在退出XenonClip...")
            
            # 停止剪贴板监听
            if self.clipboard_monitor:
                self.clipboard_monitor.stop()
            
            # 停止托盘图标
            if self.tray_icon:
                self.tray_icon.stop()
            
            # 退出程序
            sys.exit(0)
            
        except Exception as e:
            logger.error(f"退出应用失败: {e}")
    
    def run(self):
        """运行应用"""
        try:
            # 异步初始化
            if not asyncio.run(self.initialize()):
                sys.exit(1)
            
            # 启动各个组件
            self.start_server()
            self.start_clipboard_monitor()
            self.setup_hotkeys()
            self.create_tray_icon()
            
            logger.info("XenonClip启动完成")
            
            # 自动打开主界面
            time.sleep(1)
            self.show_window()
            
            # 保持主线程运行
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.quit_app()
                
        except Exception as e:
            logger.error(f"运行应用失败: {e}")
            sys.exit(1)

if __name__ == "__main__":
    app = XenonClipApp()
    app.run()