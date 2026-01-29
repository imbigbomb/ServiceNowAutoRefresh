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
import winsound  # 导入用于兜底报警

# 获取当前脚本所在的文件夹绝对路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.ini")

# --- 配置区 ---
WINDOW_TITLE_1 = "Catalog Tasks | Enterprise"
WINDOW_TITLE_2 = "Incidents | Enterprise"
DEFAULT_URL_1 = "https://your-incident-url.com"
DEFAULT_URL_2 = "https://your-sctask-url.com"
DEFAULT_INTERVAL = 120

# 建议使用 .wav 格式，兼容性更强
MP3_PATH = os.path.join(BASE_DIR, "alert.wav") 
IMAGE_FILES = {
    "Open 标签": os.path.join(BASE_DIR, "open_label.png"),
    "empty 标签": os.path.join(BASE_DIR, "empty_label.png")
}
CONFIDENCE_LEVEL = 0.8

class MonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ServiceNow工单监控")
        self.root.geometry("600x400") # 稍微增加高度以适应日志
        
        # 内部变量映射
        self.is_running = False
        self.monitor_thread = None
        
        # 加载持久化配置
        self.load_settings()
        self.setup_ui()

    def load_settings(self):
        """读取或创建 config.ini"""
        self.config = configparser.ConfigParser(interpolation=None)
        if os.path.exists(CONFIG_PATH):
            try:
                self.config.read(CONFIG_PATH, encoding='utf-8')
            except Exception as e:
                print(f"读取配置文件出错: {e}")
        
        if 'Settings' not in self.config:
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
        self.log_area = scrolledtext.ScrolledText(self.root, width=75, height=20, state='disabled', font=("Consolas", 9))
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
        """【已优化】解决长时间运行无声问题"""
        def _play():
            # 方案 A: Pygame 方案 (带重置逻辑)
            try:
                pygame.mixer.quit() # 强制关闭旧驱动连接
                pygame.mixer.init() # 重新初始化
                if os.path.exists(MP3_PATH):
                    pygame.mixer.music.load(MP3_PATH)
                    pygame.mixer.music.set_volume(0.8)
                    pygame.mixer.music.play()
                    start_time = time.time()
                    # 播放最多持续 10 秒，防止线程挂死
                    while pygame.mixer.music.get_busy() and self.is_running and (time.time() - start_time < 10):
                        time.sleep(1)
                    pygame.mixer.music.stop()
                    pygame.mixer.quit()
                    return # 播放成功直接退出
            except Exception as e:
                self.log(f"音频驱动异常: {e}")

            # 方案 B: 系统底层兜底 (System Asterisk)
            try:
                winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS)
            except:
                # 方案 C: 最终物理蜂鸣
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
                self.log(f"未找到标题包含: {title_keyword} 的窗口")
        except Exception as e:
            self.log(f"刷新失败: {title_keyword}")
        return False

    def monitor_loop(self):
        while self.is_running:
            loop_interval = self.current_interval
            
            # 1. 刷新流程
            self.refresh_windows(WINDOW_TITLE_1)
            time.sleep(1) # 增加小缓冲
            if not self.is_running: break
            self.refresh_windows(WINDOW_TITLE_2)
            
            # 2. 加载等待
            self.log(f"等待 20 秒加载页面...")
            for _ in range(20):
                if not self.is_running: return
                time.sleep(1)

            # 3. 扫描流程
            self.log("正在执行屏幕扫描...")
            found = False
            for label, path in IMAGE_FILES.items():
                if not self.is_running: break
                if not os.path.exists(path):
                    self.log(f"❌ 找不到图片文件: {path}")
                    continue
                try:
                    # 统一使用灰度模式和 0.8 置信度
                    if pyautogui.locateOnScreen(path, confidence=CONFIDENCE_LEVEL, grayscale=True):
                        self.log(f"🎯【发现工单】类型: {label}")
                        found = True
                except: pass
            
            if found: 
                self.play_alert()
            else: 
                self.log("本轮未发现新工单。")

            # 4. 周期睡眠
            wait = loop_interval - 25 if loop_interval > 25 else 1
            self.log(f"休眠中，{wait} 秒后开始下轮刷新...")
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
    # 窗口置顶，方便观察
    # root.attributes("-topmost", True) 
    app = MonitorApp(root)
    root.mainloop()
