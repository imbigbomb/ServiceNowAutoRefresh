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

# 获取当前脚本所在的文件夹绝对路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- 配置区 ---
WINDOW_TITLE_1 = "Catalog Tasks | Enterprise"
WINDOW_TITLE_2 = "Incidents | Enterprise"
URL_1 = "https://your-incident-url.com"
URL_2 = "https://your-sctask-url.com"
INTERVAL = 120

# 图片列表：只需在这里添加文件名即可
IMAGE_FILES = {
    "Open 标签": "open_label.png",
    "New 标签": "new_label.png"
}

MP3_PATH = os.path.join(BASE_DIR, "alert.wav")
CONFIDENCE_LEVEL = 0.8

# 初始化音频
pygame.mixer.init()

class MonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("工单自动监控系统 (双重检测版)")
        self.root.geometry("600x550")
        
        self.is_running = False
        self.monitor_thread = None

        self.setup_ui()
        self.check_files()

    def check_files(self):
        """检查必要文件是否存在"""
        for name, filename in IMAGE_FILES.items():
            path = os.path.join(BASE_DIR, filename)
            if not os.path.exists(path):
                self.log(f"警告: 找不到【{name}】图片文件: {filename}")
        
        if not os.path.exists(MP3_PATH):
            self.log(f"提示: 找不到音频文件 {MP3_PATH}，将使用系统蜂鸣音")

    def setup_ui(self):
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)

        self.start_btn = tk.Button(btn_frame, text="开始监控", command=self.toggle_monitor, bg="#4CAF50", fg="white", width=12, height=2)
        self.start_btn.grid(row=0, column=0, padx=10)

        self.url_btn = tk.Button(btn_frame, text="打开工单页面", command=self.open_urls, width=12, height=2)
        self.url_btn.grid(row=0, column=1, padx=10)

        self.log_area = scrolledtext.ScrolledText(self.root, width=75, height=28, state='disabled', font=("Consolas", 9))
        self.log_area.pack(padx=10, pady=10)

        self.log("系统就绪。监控目标：Open 字样 和 New 字样。")

    def log(self, message):
        now = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        full_message = f"{now} {message}\n"
        self.log_area.configure(state='normal')
        self.log_area.insert(tk.END, full_message)
        self.log_area.see(tk.END)
        self.log_area.configure(state='disabled')

    def open_urls(self):
        webbrowser.open(URL_1)
        webbrowser.open(URL_2)
        self.log("已尝试打开预设的 URL 页面")

    def toggle_monitor(self):
        if not self.is_running:
            self.is_running = True
            self.start_btn.config(text="暂停监控", bg="#f44336")
            self.log(">>> [启动] 正在进行双重图文扫描...")
            self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
            self.monitor_thread.start()
        else:
            self.is_running = False
            self.start_btn.config(text="开始监控", bg="#4CAF50")
            self.log(">>> [暂停] 监控已停止")

    def play_alert(self):
        def _play():
            if os.path.exists(MP3_PATH):
                try:
                    pygame.mixer.music.load(MP3_PATH)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy() and self.is_running:
                        time.sleep(1)
                except Exception as e:
                    self.log(f"音频播放出错: {e}")
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
                self.log(f"已刷新: {title_keyword}")
                return True
            else:
                self.log(f"未找到包含 '{title_keyword}' 的窗口")
                return False
        except Exception:
            return False

    def monitor_loop(self):
        while self.is_running:
            # 1. 刷新
            self.refresh_windows(WINDOW_TITLE_1)
            time.sleep(2)
            if not self.is_running: break
            self.refresh_windows(WINDOW_TITLE_2)
            
            # 2. 等待加载
            self.log("等待 20 秒加载页面...")
            for _ in range(20):
                if not self.is_running: return
                time.sleep(1)

            # 3. 核心扫描逻辑：遍历所有图片
            self.log("正在执行屏幕扫描 (Open & New)...")
            found_any = False
            
            for label_name, filename in IMAGE_FILES.items():
                if not self.is_running: break
                
                img_path = os.path.join(BASE_DIR, filename)
                if not os.path.exists(img_path): continue

                try:
                    target = pyautogui.locateOnScreen(img_path, confidence=CONFIDENCE_LEVEL, grayscale=True)
                    if target:
                        self.log(f"【发现新工单！】匹配类型: {label_name}")
                        found_any = True
                        # 如果一张图找到了，可以根据需要决定是否继续找下一张
                        # 这里我们只要发现一个就触发报警
                except Exception:
                    pass
            
            if found_any:
                self.play_alert()
            else:
                self.log("扫描完成：未发现异常工单。")

            # 4. 周期等待
            self.log(f"本轮结束，{INTERVAL} 秒后轮询。")
            for _ in range(INTERVAL - 25):
                if not self.is_running: return
                time.sleep(1)

if __name__ == "__main__":
    root = tk.Tk()
    app = MonitorApp(root)
    root.mainloop()
