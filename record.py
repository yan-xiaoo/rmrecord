import signal
import tkinter as tk
from tkinter import ttk,messagebox
import subprocess
import os
import sys
from datetime import datetime
import urllib.request
import json
import ctypes
import shutil

if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass


class RecordView:
    def __init__(self, view_name, view_url, output_dir, output_name, cache_dir):
        self.view_name = view_name
        self.view_url = view_url
        self.output_dir = output_dir
        self.cache_dir = cache_dir
        self.output_name = output_name
    
    def __repr__(self):
        return f"RecordView(view_name={self.view_name}, view_url={self.view_url}, output_dir={self.output_dir}, output_name={self.output_name})"
    
    def start(self, use_unique_name=True):
        if use_unique_name:
            output_full_name = os.path.join(self.output_dir, self.output_name)
            counter = 1
            while os.path.exists(output_full_name):
                name, ext = os.path.splitext(self.output_name)
                self.output_name = f"{name}_{counter}{ext}"
                output_full_name = os.path.join(self.output_dir, self.output_name)
                counter += 1
        # 启动下载进程
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        # 使用 subprocess 启动下载进程

        cmd = [m3u8dl_path, self.view_url, "--save-dir", self.output_dir, "--save-name", self.output_name, "--tmp-dir", self.cache_dir, "--live-real-time-merge", "--live-pipe-mux", "--ffmpeg-binary-path", ffmpeg_path]
        process = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        return process
    
    def clear_downloaded_file(self):
        output_file = os.path.join(self.output_dir, self.output_name)
        if os.path.exists(output_file):
            os.remove(output_file)


hint_text = "文件前缀"
live_game_info = 'https://rm-static.djicdn.com/live_json/live_game_info.json'
current_and_next_matches = 'https://rm-static.djicdn.com/live_json/current_and_next_matches.json'

timer = None

if getattr(sys,'frozen',False):
    script_dir = os.path.dirname(os.path.abspath(sys.executable))
    base_path = sys._MEIPASS # type: ignore
else:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = script_dir

def find_binary_executable(exe_name: str):
    """
    查找可执行文件的路径。
    :param exec_name: 可执行文件的名称，应当为不带扩展名的文件名。
    :return: 可执行文件的路径，如果未找到则返回 None。
    """
    if os.name == 'nt' and exe_name.endswith('.exe'):
        exe_name = exe_name[:-4]

    exe_path = shutil.which(exe_name)
    if exe_path:
        return exe_path
    exe_name = exe_name + ".exe" if os.name == 'nt' else exe_name
    local_paths = [
        os.path.join(base_path, exe_name),
        os.path.join(base_path, 'bin', exe_name),
    ]
    for path in local_paths:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    messagebox.showerror("错误", f"未找到 {exe_name}，请确保其已安装并添加到系统环境变量，或者位于此软件的 bin 文件夹中")
    sys.exit(1)

# 在初始化时查找 ffmpeg 路径
ffmpeg_path = find_binary_executable("ffmpeg")
m3u8dl_path = find_binary_executable("N_m3u8DL-RE.exe")
json_path = os.path.join(script_dir,'live_data.json')

def download_json(url):
    with urllib.request.urlopen(url) as response:
        response_data = response.read()
        return json.loads(response_data)

def get_current_matche():
    try:
        data = download_json(current_and_next_matches)
        order_number = None
        round_number = None
        blue_team = None
        red_team = None

        for item in data:
            current_match = item.get("currentMatch")
            if current_match is not None:
                order_number = current_match.get("orderNumber")
                round_number = current_match.get("round")
                blue_team = current_match["blueSide"]["player"]["team"]
                red_team = current_match["redSide"]["player"]["team"]
        
        if order_number is None or round_number is None or blue_team is None or red_team is None:
            messagebox.showwarning('提示','当前可能没有进行中的比赛')
            return

        match_info = f"第{int(order_number):02}场.{red_team['collegeName']}.{red_team['name']}.vs.{blue_team['collegeName']}.{blue_team['name']}.第{round_number}局"
        match_info = match_info.replace('（', '(').replace('）', ')')
        text_entry.delete(0, tk.END)
        text_entry.insert(0, match_info)
        text_entry.config(foreground='black')
    except:
        messagebox.showwarning('提示','当前可能没有进行中的比赛')
        return

def update_json():
    data = download_json(live_game_info)
    event_list = data['eventData']
    event = event_list[0]
    new_data = {
        "zoneName":event.get("zoneName"),
        'liveState': event.get('liveState'),
        'zoneLiveString': event.get('zoneLiveString'),
        'fpvData': event.get('fpvData'),
    }
    today_str = datetime.now().strftime('%Y-%m-%d')
    for event in event_list:
        zone_dates = event.get('zoneDate', [])
        if today_str in zone_dates:
            new_data = {
                "zoneName":event.get("zoneName"),
                'liveState': event.get('liveState'),
                'zoneLiveString': event.get('zoneLiveString'),
                'fpvData': event.get('fpvData'),
            }
            break
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=4)
    messagebox.showinfo('提示','JSON数据更新成功')


def update_record_status():
    if len(processes) == 0:
        for label in status_labels:
            label.grid_remove()
        return
    for i, task in enumerate(tasks):
        process = processes[i]
        if process.poll() is None:
            label = status_labels[i]
            label.grid()
            label.config(text=f"{task.view_name} 正在录制", style="Green.TLabel")
        elif process.poll() == 0:
            label = status_labels[i]
            label.grid()
            label.config(text=f"{task.view_name} 录制完成", style="Yellow.TLabel")
        else:
            label = status_labels[i]
            label.grid()
            label.config(text=f"{task.view_name} 录制失败", style="Red.TLabel")
            root.after(3000, restart_task, task, i)

    root.after(1000, update_record_status)


def restart_task(task, id):
    global processes
    processes[id] = task.start()

if not os.path.exists(json_path):
    update_json()

# 下载任务列表
processes = []
tasks = []
downloading = False

def start_stop_downloads():
    global downloading
    if downloading:
        stop_downloads()
        download_button.config(text="开始录制")
    else:
        start_downloads()
        download_button.config(text="停止录制")
    downloading = not downloading

def find_src_by_label(data, label):
    for item in data:
        if item['label'] == label:
            return item['src']
    return None

def file_list():
    global main_view_var,base_view_var,red_team_var,blue_team_var,resolution_combobox
    files = []
    resolution = resolution_combobox.get()
    with open(json_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
        zonelive = data['zoneLiveString']
        src = find_src_by_label(zonelive,resolution)
        if main_view_var.get():
            files.append(('全场', src))
        for fpv in data['fpvData']:
            role = fpv['role']
            if "半场" in role or "号机" in role:
                if base_view_var.get():
                    src = find_src_by_label(fpv['sources'], resolution)
                    files.append((role, src))
            else:
                if "红" in role and red_team_var.get():
                    src = find_src_by_label(fpv['sources'], resolution)
                    files.append((role, src))
                elif "蓝" in role and blue_team_var.get():
                    src = find_src_by_label(fpv['sources'], resolution)
                    files.append((role, src))
    return files

def get_unique_folder(base_dir,out_dir,cache_dir,folder_name):
    output_folder = os.path.join(base_dir, out_dir, folder_name)
    cache_folder = os.path.join(base_dir, cache_dir, folder_name)
    counter = 1
    unique_folder = output_folder
    while os.path.exists(unique_folder):
        unique_folder = f"{output_folder}_{counter}"
        counter += 1
    os.makedirs(unique_folder)
    os.makedirs(cache_folder, exist_ok=True)
    return unique_folder, cache_folder

def start_downloads():
    global processes, tasks
    files = file_list()
    dirmane = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 设置录制文件前缀
    game_info = text_entry.get()
    if game_info == hint_text:
        game_info = ''
    if game_info != '':
        dirmane = game_info.split('.')[0]
        game_info = game_info+'_'
    output_folder, cache_folder = get_unique_folder(script_dir,'output', "cache", dirmane)
    os.makedirs(output_folder, exist_ok=True)
    os.makedirs(cache_folder, exist_ok=True)
    # 创建并行下载的 subprocess 任务
    processes = []
    tasks.clear()
    for file in files:
        output_file = game_info+file[0]
        task = RecordView(file[0], file[1], output_folder, output_file, cache_folder)
        tasks.append(task)
        process = task.start()
        processes.append(process)

    root.after(1000, update_record_status)

def stop_downloads():
    global processes, tasks
    for process in processes:
        if process.poll() is None:
            # process.send_signal(signal.CTRL_C_EVENT)
            process.terminate()
    # 等待所有子进程完成
    for process in processes:
        process.wait()
    processes.clear()
    tasks.clear()

def on_closing():
    if downloading:
        stop_downloads()
    # 关闭窗口
    root.destroy()

def center_window(root):
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    window_width = root.winfo_width()
    window_height = root.winfo_height()
    x = (screen_width // 2) - (window_width // 2)
    y = (screen_height // 2) - (window_height // 2)
    root.geometry(f"+{x}+{y}")
    root.minsize(window_width, window_height)
    rows = frame.grid_size()[1]
    for i in range(rows):
        frame.grid_rowconfigure(i, weight=1)
    columns = frame.grid_size()[0]
    for i in range(columns):
        frame.grid_columnconfigure(i, weight=1)

# 创建主窗口
root = tk.Tk()
root.withdraw()
root.title("RMrecord")
root.iconbitmap(os.path.join(base_path,'icon.ico'))
root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(0, weight=1)
# 创建菜单栏
menu_bar = tk.Menu(root)
root.config(menu=menu_bar)
menu_bar.add_command(label="更新 JSON", command=update_json)
menu_bar.add_command(label="获取比赛信息", command=get_current_matche)
frame = ttk.Frame(root)
frame.grid(row=0, column=0, padx=28, pady=10,sticky='nsew')  # 使用 grid 布局

# 创建下拉选择控件
resolution_combobox = ttk.Combobox(frame, values=["540p", "720p", "1080p"])
resolution_combobox.current(1)  # 将当前选项设置为 720p
resolution_combobox.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky='ew')

main_view_var = tk.BooleanVar()
red_team_var = tk.BooleanVar()
blue_team_var = tk.BooleanVar()
base_view_var = tk.BooleanVar()

main_view_check = ttk.Checkbutton(frame, text="全场", variable=main_view_var)
main_view_check.grid(row=1, column=0, padx=8, pady=0, sticky='ew')

base_view_check = ttk.Checkbutton(frame, text="半场", variable=base_view_var)
base_view_check.grid(row=1, column=1, padx=8, pady=0, sticky='ew')

red_team_check = ttk.Checkbutton(frame, text="红方操作手", variable=red_team_var)
red_team_check.grid(row=2, column=0, padx=8, pady=0, sticky='ew')

blue_team_check = ttk.Checkbutton(frame, text="蓝方操作手", variable=blue_team_var)
blue_team_check.grid(row=2, column=1, padx=8, pady=0, sticky='ew')

download_button = ttk.Button(frame, text="开始录制", command=start_stop_downloads)
download_button.grid(row=3, column=0, columnspan=2,padx=10,pady=10, sticky='ew')

def on_entry_focus_in(event):
    if text_entry.get() == hint_text:
        text_entry.delete(0, tk.END)
        text_entry.config(foreground='black')

def on_entry_focus_out(event):
    if text_entry.get() == "":
        text_entry.insert(0, hint_text)
        text_entry.config(foreground='grey')

# 添加单行文本框
text_entry = ttk.Entry(frame, foreground='grey')
text_entry.insert(0, hint_text)
text_entry.bind("<FocusIn>", on_entry_focus_in)
text_entry.bind("<FocusOut>", on_entry_focus_out)
text_entry.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky='ew')

status_labels = []
green_text_label_style = ttk.Style()
green_text_label_style.configure("Green.TLabel", foreground="green")
red_text_label_style = ttk.Style()
red_text_label_style.configure("Red.TLabel", foreground="red")
yellow_text_label_style = ttk.Style()
yellow_text_label_style.configure("Yellow.TLabel", foreground="yellow")
for i in range(15):
    label = ttk.Label(frame, text="", anchor='w')
    label.grid(row=5 + int(i / 2), column=i % 2, padx=10, pady=0, sticky='ew')
    # 先隐藏
    label.grid_remove()
    status_labels.append(label)

# 设置窗口关闭时的处理函数
root.protocol("WM_DELETE_WINDOW", on_closing)
center_window(root)
root.deiconify()
# 启动主循环
root.mainloop()