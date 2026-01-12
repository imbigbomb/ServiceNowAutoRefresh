import pyautogui
import pygetwindow as gw
import time
import pygame
import threading
import os
import webbrowser
import tkinter as tk
from tkinter import scrolledtext
from datetime import datetime

# --- 配置区 ---
WINDOW_TITLE_1 = "Catalog Tasks | Enterprise"
WINDOW_TITLE_2 = "Incidents | Enterprise"
URL_1 = "https://your-incident-url.com"  # 请替换为实际 URL
URL_2 = "https://your-sctask-url.com"    # 请替换为实际 URL
INTERVAL = 120
MP3_PATH = r"C:\Users\shuguyu\Desktop\alert_jpn.mp3"
IMAGE_PATH = r"C:\Users\shuguyu\Desktop\open_label.png"
CONFIDENCE_LEVEL = 0.8

# 初始化音频
pygame.mixer.init()

class MonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("工单自动监控系统")
        self.root.geometry("600x450")
        
        # 运行状态控制
        self.is_running = False
        self.monitor_thread = None

        self.setup_ui()

    def setup_ui(self):
        # 按钮容器
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)

        # 开始/暂停按钮
        self.start_btn = tk.Button(btn_frame, text="开始监控", command=self.toggle_monitor, bg="#4CAF50", fg="white", width=12)
        self.start_btn.grid(row=0, column=0, padx=5)

        # 呼出 URL 按钮
        self.url_btn = tk.Button(btn_frame, text="打开工单页面", command=self.open_urls, width=12)
        self.url_btn.grid(row=0, column=1, padx=5)

        # 日志显示区域
        self.log_area = scrolledtext.ScrolledText(self.root, width=70, height=20, state='disabled')
        self.log_area.pack(padx=10, pady=10)

        # 初始欢迎词
        self.log("系统就绪，点击“开始监控”启动程序。")

    def log(self, message):
        """在 GUI 界面打印带时间戳的日志"""
        now = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        full_message = f"{now} {message}\n"
        
        self.log_area.configure(state='normal')
        self.log_area.insert(tk.END, full_message)
        self.log_area.see(tk.END)  # 自动滚动到底部
        self.log_area.configure(state='disabled')

    def open_urls(self):
        """打开预设的 URL"""
        webbrowser.open(URL_1)
        webbrowser.open(URL_2)
        self.log("已尝试在浏览器中打开 URL")

    def toggle_monitor(self):
        """切换监控状态"""
        if not self.is_running:
            self.is_running = True
            self.start_btn.config(text="暂停监控", bg="#f44336")
            self.log(">>> 监控已启动")
            self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
            self.monitor_thread.start()
        else:
            self.is_running = False
            self.start_btn.config(text="开始监控", bg="#4CAF50")
            self.log(">>> 监控已暂停")

    def play_alert(self):
        def _play():
            if os.path.exists(MP3_PATH):
                pygame.mixer.music.load(MP3_PATH)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy() and self.is_running:
                    time.sleep(1)
            else:
                import winsound
                winsound.Beep(1000, 1000)
        threading.Thread(target=_play, daemon=True).start()

    def refresh_windows(self, title_keyword):
        try:
            windows = gw.getWindowsWithTitle(title_keyword)
            if windows:
                win = windows[0]
                if win.isMinimized: win.restore()
                win.activate()
                time.sleep(1)
                pyautogui.press('f5')
                self.log(f"已刷新窗口: {title_keyword}")
                return True
            else:
                self.log(f"未找到窗口: {title_keyword}")
                return False
        except Exception as e:
            self.log(f"刷新出错: {e}")
            return False

    def monitor_loop(self):
        """后台监控循环"""
        while self.is_running:
            # 1. 刷新
            self.refresh_windows(WINDOW_TITLE_1)
            time.sleep(2)
            if not self.is_running: break
            
            self.refresh_windows(WINDOW_TITLE_2)
            
            # 2. 等待加载
            self.log("等待 20 秒页面加载...")
            for _ in range(20): # 分步等待以便能快速响应“暂停”
                if not self.is_running: return
                time.sleep(1)

            # 3. 扫描
            self.log("正在扫描屏幕中的新工单...")
            try:
                target = pyautogui.locateOnScreen(IMAGE_PATH, confidence=CONFIDENCE_LEVEL, grayscale=True)
                if target:
                    self.log("【检测到新工单！】")
                    self.play_alert()
            except Exception:
                pass

            # 4. 周期睡眠
            self.log(f"一轮检查完成。{INTERVAL}秒后开始下一轮。")
            for _ in range(INTERVAL - 25):
                if not self.is_running: return
                time.sleep(1)

if __name__ == "__main__":
    root = tk.Tk()
    app = MonitorApp(root)
    root.mainloop()