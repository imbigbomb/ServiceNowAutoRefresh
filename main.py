import pyautogui
import pygetwindow as gw
import time
import pygame
import threading
import os
import webbrowser
import tkinter as tk
from tkinter import scrolledtext, messagebox
from datetime import datetime
import configparser

# 获取当前脚本所在的文件夹绝对路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.ini")

# --- 配置区 ---
WINDOW_TITLE_1 = "Catalog Tasks | Enterprise"
WINDOW_TITLE_2 = "Incidents | Enterprise"
# 下面三个值将由配置文件驱动，若无配置文件则使用以下默认值
DEFAULT_URL_1 = "https://your-incident-url.com"
DEFAULT_URL_2 = "https://your-sctask-url.com"
DEFAULT_INTERVAL = 120

MP3_PATH = os.path.join(BASE_DIR, "alert.wav")
IMAGE_FILES = {
    "Open 标签": os.path.join(BASE_DIR, "open_label.png"),
    "empty 标签": os.path.join(BASE_DIR, "empty_label.png")
}
CONFIDENCE_LEVEL = 0.8

# 初始化音频
pygame.mixer.init()

class MonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ServiceNow工单监控")
        self.root.geometry("600x300")
        
        # 内部变量映射
        self.is_running = False
        self.monitor_thread = None
        
        # 加载持久化配置
        self.load_settings()
        self.setup_ui()

    def load_settings(self):
        """读取或创建 config.ini"""
        self.config = configparser.ConfigParser()
        if os.path.exists(CONFIG_PATH):
            self.config.read(CONFIG_PATH, encoding='utf-8')
        else:
            self.config['Settings'] = {
                'url_1': DEFAULT_URL_1,
                'url_2': DEFAULT_URL_2,
                'interval': str(DEFAULT_INTERVAL)
            }
            self.save_settings_to_file()
        
        self.current_url_1 = self.config.get('Settings', 'url_1')
        self.current_url_2 = self.config.get('Settings', 'url_2')
        self.current_interval = self.config.getint('Settings', 'interval')

    def save_settings_to_file(self):
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            self.config.write(f)

    def setup_ui(self):
        # 按钮区
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)

        self.start_btn = tk.Button(btn_frame, text="开始监控", command=self.toggle_monitor, bg="#4CAF50", fg="white", width=12, height=2)
        self.start_btn.grid(row=0, column=0, padx=5)

        self.url_btn = tk.Button(btn_frame, text="打开网页", command=self.open_urls, width=12, height=2)
        self.url_btn.grid(row=0, column=1, padx=5)

        self.settings_btn = tk.Button(btn_frame, text="⚙ 设置", command=self.open_settings_window, width=8, height=2)
        self.settings_btn.grid(row=0, column=2, padx=5)

        # 日志区
        self.log_area = scrolledtext.ScrolledText(self.root, width=75, height=30, state='disabled', font=("Consolas", 9))
        self.log_area.pack(padx=10, pady=10)
        self.log("读取配置成功")

    def open_settings_window(self):
        """弹出二级设置菜单"""
        win = tk.Toplevel(self.root)
        win.title("自定义参数")
        win.geometry("400x250")
        win.grab_set()

        tk.Label(win, text="URL 1 (Incidents):").grid(row=0, column=0, padx=10, pady=10, sticky="e")
        e1 = tk.Entry(win, width=35)
        e1.insert(0, self.current_url_1)
        e1.grid(row=0, column=1)

        tk.Label(win, text="URL 2 (SCTASK):").grid(row=1, column=0, padx=10, pady=10, sticky="e")
        e2 = tk.Entry(win, width=35)
        e2.insert(0, self.current_url_2)
        e2.grid(row=1, column=1)

        tk.Label(win, text="扫描间隔 (秒):").grid(row=2, column=0, padx=10, pady=10, sticky="e")
        e3 = tk.Entry(win, width=10)
        e3.insert(0, str(self.current_interval))
        e3.grid(row=2, column=1, sticky="w")

        def save_and_close():
            try:
                self.current_url_1 = e1.get()
                self.current_url_2 = e2.get()
                self.current_interval = int(e3.get())
                
                self.config.set('Settings', 'url_1', self.current_url_1)
                self.config.set('Settings', 'url_2', self.current_url_2)
                self.config.set('Settings', 'interval', str(self.current_interval))
                self.save_settings_to_file()
                
                self.log("配置已更新并存入 config.ini")
                win.destroy()
            except ValueError:
                messagebox.showerror("错误", "间隔时间必须是整数数字")

        tk.Button(win, text="保存设置", command=save_and_close, bg="#2196F3", fg="white", width=10).grid(row=3, column=0, columnspan=2, pady=15)

    def log(self, message):
        now = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        self.log_area.configure(state='normal')
        self.log_area.insert(tk.END, f"{now} {message}\n")
        self.log_area.see(tk.END)
        self.log_area.configure(state='disabled')

    def open_urls(self):
        webbrowser.open(self.current_url_1)
        webbrowser.open(self.current_url_2)
        self.log("已弹出浏览器窗口。")

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
        except Exception as e:
            self.log(f"刷新失败: {title_keyword}")
        return False

    def monitor_loop(self):
        while self.is_running:
            # 记录本轮使用的间隔，防止中途修改导致等待逻辑混乱
            loop_interval = self.current_interval
            
            # 1. 刷新流程
            self.refresh_windows(WINDOW_TITLE_1)
            time.sleep(2)
            if not self.is_running: break
            self.refresh_windows(WINDOW_TITLE_2)
            
            # 2. 加载等待
            self.log("等待 20 秒加载页面...")
            for _ in range(20):
                if not self.is_running: return
                time.sleep(1)

            # 3. 扫描流程 (保持原有双图逻辑)
            self.log("正在执行屏幕扫描...")
            found = False
            for label, path in IMAGE_FILES.items():
                if not self.is_running: break
                try:
                    if pyautogui.locateOnScreen(path, confidence=CONFIDENCE_LEVEL, grayscale=True):
                        self.log(f"【发现工单】类型: {label}")
                        found = True
                except: pass
            
            if found: self.play_alert()
            else: self.log("本轮未发现新工单。")

            # 4. 周期睡眠
            wait = loop_interval - 25 if loop_interval > 25 else 1
            self.log(f"本轮结束，{wait} 秒后重试。")
            for _ in range(wait):
                if not self.is_running: return
                time.sleep(1)

    def toggle_monitor(self):
        if not self.is_running:
            self.is_running = True
            self.start_btn.config(text="暂停监控", bg="#f44336")
            self.log(f">>> [启动] 设定间隔: {self.current_interval}s")
            self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
            self.monitor_thread.start()
        else:
            self.is_running = False
            self.start_btn.config(text="开始监控", bg="#4CAF50")
            self.log(">>> [暂停] 监控已停止")

if __name__ == "__main__":
    root = tk.Tk()
    app = MonitorApp(root)
    root.mainloop()
