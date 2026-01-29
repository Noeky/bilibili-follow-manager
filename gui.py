import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import json
import os
import sys
import time
from bilibili_api import BilibiliAPI
from auto_login import auto_login_setup

def get_app_dir():
    """获取应用程序目录"""
    if getattr(sys, 'frozen', False):
        # 打包后的可执行文件
        return os.path.dirname(sys.executable)
    else:
        # 开发环境
        return os.path.dirname(os.path.abspath(__file__))

class BilibiliManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("B站关注管理器")
        self.root.geometry("968x732")
        self.root.minsize(800, 600)
    
        self.setup_theme()
        
        self.api = None
        self.following_list = []
        self.checked_items = {}  # 存储选中状态
        self.item_data = {}      # 存储 tree item ID 到完整用户数据的映射
        
        self.create_widgets()
        self.check_config()
    
    def setup_theme(self):
        style = ttk.Style()
        
        try:
            style.theme_use('vista')  # Windows现代主题
        except:
            style.theme_use('clam')   # 备用主题
        
        self.colors = {
            'primary': '#00A1D6',      
            'primary_dark': '#0084B4',
            'success': '#52C41A',
            'warning': '#FAAD14',
            'danger': '#FF4D4F',
            'bg_light': '#F8F9FA',
            'bg_dark': '#FFFFFF',
            'text_primary': '#262626',
            'text_secondary': '#8C8C8C',
            'border': '#D9D9D9'
        }
        
        # 配置按钮样式
        style.configure('Primary.TButton',
                       foreground='white',
                       padding=(20, 10),
                       font=('Microsoft YaHei UI', 10, 'bold'))
        
        style.map('Primary.TButton',
                 background=[('active', self.colors['primary_dark']),
                           ('!active', self.colors['primary']),
                           ('pressed', self.colors['primary_dark'])],
                 foreground=[('active', 'white'),
                           ('!active', 'white'),
                           ('pressed', 'white')])
        
        style.configure('Success.TButton',
                       padding=(15, 8),
                       font=('Microsoft YaHei UI', 9))
        
        style.configure('Danger.TButton',
                       padding=(15, 8),
                       font=('Microsoft YaHei UI', 9))
        
        # 设置根窗口背景
        self.root.configure(bg=self.colors['bg_light'])
    
    def create_widgets(self):
        # 主容器
        main_container = tk.Frame(self.root, bg=self.colors['bg_light'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 标题区域
        title_frame = tk.Frame(main_container, bg=self.colors['bg_light'])
        title_frame.pack(fill=tk.X, pady=(0, 25))
        
        title_label = tk.Label(title_frame, 
                              text="🎬 B站关注管理器", 
                              font=("Microsoft YaHei UI", 24, "bold"),
                              fg=self.colors['primary'],
                              bg=self.colors['bg_light'])
        title_label.pack()
        
        subtitle_label = tk.Label(title_frame,
                                 text="轻松管理你的B站关注列表",
                                 font=("Microsoft YaHei UI", 11),
                                 fg=self.colors['text_secondary'],
                                 bg=self.colors['bg_light'])
        subtitle_label.pack(pady=(5, 0))
        
        # 登录状态卡片
        login_card = ttk.LabelFrame(main_container, text="  登录状态  ", padding=20)
        login_card.pack(fill=tk.X, pady=(0, 20))
        
        status_frame = tk.Frame(login_card, bg=self.colors['bg_dark'])
        status_frame.pack(fill=tk.X)
        
        # 状态指示器
        self.status_indicator = tk.Label(status_frame, text="●", font=("Arial", 16), 
                                        fg=self.colors['danger'], bg=self.colors['bg_dark'])
        self.status_indicator.pack(side=tk.LEFT, padx=(0, 10))
        
        self.status_label = tk.Label(status_frame, text="未登录", 
                                    font=("Microsoft YaHei UI", 12, "bold"),
                                    fg=self.colors['text_primary'], bg=self.colors['bg_dark'])
        self.status_label.pack(side=tk.LEFT)
        
        self.login_button = tk.Button(status_frame, text="🔐 设置登录", 
                                     command=self.setup_login,
                                     bg=self.colors['primary'],
                                     fg='white',
                                     font=('Microsoft YaHei UI', 10, 'bold'),
                                     relief='flat',
                                     padx=20, pady=8,
                                     cursor='hand2',
                                     activebackground=self.colors['primary_dark'],
                                     activeforeground='white')
        self.login_button.pack(side=tk.RIGHT)
        
        self.user_info_label = tk.Label(login_card, text="", 
                                       font=("Microsoft YaHei UI", 10),
                                       fg=self.colors['text_secondary'], 
                                       bg=self.colors['bg_dark'])
        self.user_info_label.pack(anchor=tk.W, pady=(10, 0))
        
        # 操作按钮区域
        button_frame = tk.Frame(main_container, bg=self.colors['bg_light'])
        button_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.refresh_button = tk.Button(button_frame, text="🔄 刷新关注列表", 
                                        command=self.refresh_following, 
                                        state="disabled",
                                        bg=self.colors['success'],
                                        fg='white',
                                        font=('Microsoft YaHei UI', 9),
                                        relief='flat',
                                        padx=15, pady=8,
                                        cursor='hand2',
                                        activebackground='#45B315',
                                        activeforeground='white',
                                        disabledforeground='lightgray')
        self.refresh_button.pack(side=tk.LEFT, padx=(0, 15))
        
        self.batch_unfollow_button = tk.Button(button_frame, text="❌ 批量取消关注", 
                                               command=self.batch_unfollow, 
                                               state="disabled",
                                               bg=self.colors['danger'],
                                               fg='white',
                                               font=('Microsoft YaHei UI', 9),
                                               relief='flat',
                                               padx=15, pady=8,
                                               cursor='hand2',
                                               activebackground='#E6393C',
                                               activeforeground='white',
                                               disabledforeground='lightgray')
        self.batch_unfollow_button.pack(side=tk.LEFT, padx=(0, 15))
        
        self.export_button = tk.Button(button_frame, text="📥 导出所选用户", 
                                       command=self.export_list, 
                                       state="disabled",
                                       bg='#1890FF',
                                       fg='white',
                                       font=('Microsoft YaHei UI', 9),
                                       relief='flat',
                                       padx=15, pady=8,
                                       cursor='hand2',
                                       activebackground='#0969CC',
                                       activeforeground='white',
                                       disabledforeground='lightgray')
        self.export_button.pack(side=tk.LEFT, padx=(0, 15))
        
        self.import_follow_button = tk.Button(button_frame, text="📤 导入关注", 
                                             command=self.import_and_follow, 
                                             state="disabled",
                                             bg='#52C41A',
                                             fg='white',
                                             font=('Microsoft YaHei UI', 9),
                                             relief='flat',
                                             padx=15, pady=8,
                                             cursor='hand2',
                                             activebackground='#389E0D',
                                             activeforeground='white',
                                             disabledforeground='lightgray')
        self.import_follow_button.pack(side=tk.LEFT, padx=(0, 15))
        
        # 关于按钮
        self.about_button = tk.Button(button_frame, text="ℹ️ 关于", 
                                     command=self.show_about, 
                                     bg='#722ED1',
                                     fg='white',
                                     font=('Microsoft YaHei UI', 9),
                                     relief='flat',
                                     padx=15, pady=8,
                                     cursor='hand2',
                                     activebackground='#531DAB',
                                     activeforeground='white')
        self.about_button.pack(side=tk.LEFT)
        

        
        # 关注列表卡片
        list_card = ttk.LabelFrame(main_container, text="  关注列表  ", padding=15)
        list_card.pack(fill=tk.BOTH, expand=True)
        
        # 列表工具栏
        list_toolbar = tk.Frame(list_card, bg=self.colors['bg_dark'])
        list_toolbar.pack(fill=tk.X, pady=(0, 15))

                
        self.batch_check_button = tk.Button(list_toolbar, text="批量勾选", 
                                           command=self.batch_check_selected, state="disabled",
                                           bg='#F0F0F0',
                                           fg=self.colors['text_primary'],
                                           font=('Microsoft YaHei UI', 8),
                                           relief='flat',
                                           padx=12, pady=5,
                                           cursor='hand2',
                                           activebackground='#E0E0E0')
        self.batch_check_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.batch_uncheck_button = tk.Button(list_toolbar, text="批量取消勾选", 
                                           command=self.batch_uncheck_selected, state="disabled",
                                           bg='#F0F0F0',
                                           fg=self.colors['text_primary'],
                                           font=('Microsoft YaHei UI', 8),
                                           relief='flat',
                                           padx=12, pady=5,
                                           cursor='hand2',
                                           activebackground='#E0E0E0')
        self.batch_uncheck_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.select_all_button = tk.Button(list_toolbar, text="全选", 
                                           command=self.select_all, state="disabled",
                                           bg='#F0F0F0',
                                           fg=self.colors['text_primary'],
                                           font=('Microsoft YaHei UI', 8),
                                           relief='flat',
                                           padx=12, pady=5,
                                           cursor='hand2',
                                           activebackground='#E0E0E0')
        self.select_all_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.select_none_button = tk.Button(list_toolbar, text="取消全选", 
                                            command=self.select_none, state="disabled",
                                            bg='#F0F0F0',
                                            fg=self.colors['text_primary'],
                                            font=('Microsoft YaHei UI', 8),
                                            relief='flat',
                                            padx=12, pady=5,
                                            cursor='hand2',
                                            activebackground='#E0E0E0')
        self.select_none_button.pack(side=tk.LEFT)
        
        self.count_label = tk.Label(list_toolbar, text="共 0 个关注", 
                                   font=("Microsoft YaHei UI", 10),
                                   fg=self.colors['text_secondary'], 
                                   bg=self.colors['bg_dark'])
        self.count_label.pack(side=tk.RIGHT)
        
        # 创建表格容器
        table_frame = tk.Frame(list_card, bg=self.colors['bg_dark'])
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建Treeview
        columns = ("用户名", "UID", "关注时间", "签名")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="tree headings", height=15, selectmode="extended")
        
        # 设置列标题
        self.tree.heading("#0", text="✓")
        self.tree.heading("用户名", text="👤 用户名")
        self.tree.heading("UID", text="🆔 UID")
        self.tree.heading("关注时间", text="⏰ 关注时间")
        self.tree.heading("签名", text="📝 签名")
        
        # 设置列宽
        self.tree.column("#0", width=60, minwidth=60)
        self.tree.column("用户名", width=180, minwidth=150)
        self.tree.column("UID", width=120, minwidth=100)
        self.tree.column("签名", width=300, minwidth=200)
        self.tree.column("关注时间", width=160, minwidth=140)
        
        # 绑定点击事件
        self.tree.bind("<ButtonRelease-1>", self.on_tree_click)
        
        # 滚动条
        scrollbar_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar_y.set)
        
        # 布局
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 状态栏
        status_frame = tk.Frame(main_container, bg=self.colors['bg_light'], height=30)
        status_frame.pack(fill=tk.X, pady=(15, 0))
        status_frame.pack_propagate(False)
        
        self.status_bar = tk.Label(status_frame, text="🎯 准备就绪", 
                                  font=("Microsoft YaHei UI", 10),
                                  fg=self.colors['text_secondary'],
                                  bg=self.colors['bg_light'], anchor=tk.W)
        self.status_bar.pack(fill=tk.BOTH, padx=10, pady=5)
    
    def check_config(self):
        config_path = os.path.join(get_app_dir(), 'config.json')
        if os.path.exists(config_path):
            try:
                self.api = BilibiliAPI()
                user_info = self.api.get_user_info()
                if user_info:
                    self.status_indicator.config(fg=self.colors['success'])
                    self.status_label.config(text="已登录", fg=self.colors['success'])
                    self.user_info_label.config(text=f"👋 欢迎回来，{user_info.get('uname', '未知')} (ID: {user_info.get('mid', '未知')})")
                    self.login_button.config(text="🚪 退出登录", command=self.logout, bg=self.colors['danger'])
                    self.enable_buttons()
                    self.update_status("✅ 登录成功，可以开始使用了")
                else:
                    self.status_indicator.config(fg=self.colors['warning'])
                    self.status_label.config(text="登录已过期", fg=self.colors['warning'])
                    self.login_button.config(text="🔐 设置登录", command=self.setup_login, bg=self.colors['primary'])
                    self.update_status("⚠️ 登录信息已过期，请重新设置")
            except Exception:
                self.status_indicator.config(fg=self.colors['danger'])
                self.status_label.config(text="配置错误", fg=self.colors['danger'])
                self.login_button.config(text="🔐 设置登录", command=self.setup_login, bg=self.colors['primary'])
                self.update_status("❌ 配置文件错误")
        else:
            self.login_button.config(text="🔐 设置登录", command=self.setup_login, bg=self.colors['primary'])
            self.update_status("💡 首次使用？点击\"设置登录\"开始吧")
    
    def setup_login(self):
        def login_thread():
            self.update_status("🔄 正在设置登录...")
            self.login_button.config(state="disabled")
            
            try:
                success = auto_login_setup()
                if success:
                    self.root.after(0, self.login_success)
                else:
                    self.root.after(0, self.login_failed)
            except Exception:
                self.root.after(0, self.login_failed)
        
        thread = threading.Thread(target=login_thread)
        thread.daemon = True
        thread.start()
    
    def logout(self):
        """退出登录，删除配置文件"""
        # 确认退出
        if not messagebox.askyesno("🚪 确认退出", 
                                  "确定要退出登录吗？\n\n这将删除本地保存的登录信息，\n下次需要重新登录。", 
                                  icon="question"):
            return
        
        try:
            # 删除配置文件
            config_path = os.path.join(get_app_dir(), 'config.json')
            if os.path.exists(config_path):
                os.remove(config_path)
            
            # 重置API对象
            self.api = None
            
            # 重置UI状态
            self.status_indicator.config(fg=self.colors['danger'])
            self.status_label.config(text="未登录", fg=self.colors['text_primary'])
            self.user_info_label.config(text="")
            self.login_button.config(text="🔐 设置登录", command=self.setup_login, bg=self.colors['primary'])
            
            # 禁用所有功能按钮
            self.refresh_button.config(state="disabled")
            self.batch_unfollow_button.config(state="disabled")
            self.export_button.config(state="disabled")
            self.import_follow_button.config(state="disabled")
            self.select_all_button.config(state="disabled")
            self.select_none_button.config(state="disabled")
            self.batch_check_button.config(state="disabled")
            self.batch_uncheck_button.config(state="disabled")
            
            # 清空关注列表
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.following_list = []
            self.count_label.config(text="共 0 个关注")
            
            # 更新状态
            self.update_status("🚪 已退出登录，点击\"设置登录\"重新开始")
            messagebox.showinfo("🎉 退出成功", "已成功退出登录！")
            
        except Exception as e:
            messagebox.showerror("❌ 错误", f"退出登录失败：{str(e)}")
            self.update_status("❌ 退出登录失败")

    def login_success(self):
        self.login_button.config(state="normal")
        messagebox.showinfo("🎉 成功", "登录设置成功！")
        self.check_config()  # 重新检查配置，更新按钮状态
    
    def login_failed(self):
        self.login_button.config(state="normal")
        messagebox.showerror("❌ 错误", "登录设置失败")
        self.update_status("❌ 登录设置失败")
    
    def enable_buttons(self):
        self.refresh_button.config(state="normal")
        self.batch_unfollow_button.config(state="normal")
        self.export_button.config(state="normal")
        self.import_follow_button.config(state="normal")
        self.select_all_button.config(state="normal")
        self.select_none_button.config(state="normal")
        self.batch_check_button.config(state="normal")
        self.batch_uncheck_button.config(state="normal")
    
    def refresh_following(self):
        def refresh_thread():
            self.root.after(0, lambda: self.refresh_button.config(state="disabled"))
            self.root.after(0, lambda: self.update_status("🔄 正在获取关注列表..."))
            
            try:
                if self.api is None:
                    self.root.after(0, lambda: messagebox.showerror("❌ 错误", "请先登录以获取关注列表"))
                    self.root.after(0, self.refresh_failed)
                    return
                following_list = self.api.get_all_following()
                self.root.after(0, lambda: self.update_following_list(following_list))
            except Exception:
                self.root.after(0, self.refresh_failed)
        
        thread = threading.Thread(target=refresh_thread)
        thread.daemon = True
        thread.start()
    
    def update_following_list(self, following_list):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.following_list = following_list
        self.checked_items = {}  # 重置选中状态
        self.item_data = {}      # 重置数据映射
        
        for user in following_list:
            # 格式化时间显示
            mtime_str = user.get('mtime_str', '未知')
            
            # 获取签名，如果为空则显示默认值
            sign = user.get('sign', '').strip()
            if not sign:
                sign = '暂无签名'
            
            # 插入时设置默认为未选中
            item_id = self.tree.insert("", tk.END, text="☐", values=(
                user.get('uname', '未知'),
                user.get('mid', ''),
                mtime_str,
                sign
            ))
            self.checked_items[item_id] = False
            self.item_data[item_id] = user  # 保存完整的用户数据
        
        self.refresh_button.config(state="normal")
        self.count_label.config(text=f"共 {len(following_list)} 个关注")
        self.update_status(f"✅ 已加载 {len(following_list)} 个关注用户")
    
    def refresh_failed(self):
        self.refresh_button.config(state="normal")
        messagebox.showerror("❌ 错误", "获取关注列表失败")
        self.update_status("❌ 获取关注列表失败")
    
    def select_all(self):
        for item in self.tree.get_children():
            self.checked_items[item] = True
            self.tree.item(item, text="☑")
            self.tree.selection_add(item)
    
    def select_none(self):
        for item in self.tree.get_children():
            self.checked_items[item] = False
            self.tree.item(item, text="☐")
        self.tree.selection_remove(self.tree.selection())
    
    def batch_check_selected(self):
        """批量勾选树视图中当前选中的项目"""
        selected_items = self.tree.selection()
        
        if not selected_items:
            messagebox.showinfo("提示", "请先用鼠标点击选择要勾选的行（可按住Ctrl或Shift多选）")
            return
            
        # 勾选所有选中的项
        for item in selected_items:
            self.checked_items[item] = True
            self.tree.item(item, text="☑")
        
        # 更新状态
        self.update_status(f"✅ 已批量勾选 {len(selected_items)} 个项目")
    
    def batch_uncheck_selected(self):
        """批量取消勾选树视图中当前选中的项目"""
        selected_items = self.tree.selection()
        
        if not selected_items:
            messagebox.showinfo("提示", "请先用鼠标点击选择要取消勾选的行（可按住Ctrl或Shift多选）")
            return
            
        # 取消勾选所有选中的项
        for item in selected_items:
            self.checked_items[item] = False
            self.tree.item(item, text="☐")
            # 同时从树的选择中移除（可选，根据需求决定）
            # self.tree.selection_remove(item)
        
        # 更新状态
        self.update_status(f"✅ 已批量取消勾选 {len(selected_items)} 个项目")
    
    def batch_unfollow(self):
        selected_items = [item for item, checked in self.checked_items.items() if checked]
        if not selected_items:
            messagebox.showwarning("⚠️ 警告", "请先选择要取消关注的用户")
            return
        
        count = len(selected_items)
        if not messagebox.askyesno("⚠️ 确认操作", 
                                  f"确定要取消关注 {count} 个用户吗？\n\n⚠️ 此操作不可撤销！", 
                                  icon="warning"):
            return
        
        def unfollow_thread():
            self.root.after(0, lambda: self.batch_unfollow_button.config(state="disabled"))
            
            success_count = 0
            for item in selected_items:
                try:
                    values = self.tree.item(item)['values']
                    uid = int(values[1])
                    username = values[0]
                    
                    self.root.after(0, lambda u=username: self.update_status(f"🔄 正在取消关注: {u}"))
                    
                    if self.api and hasattr(self.api, "unfollow_user") and callable(getattr(self.api, "unfollow_user")):
                        if self.api.unfollow_user(uid):
                            success_count += 1
                            self.root.after(0, lambda i=item: self.tree.delete(i))
                    else:
                        raise AttributeError("API对象未实现unfollow_user方法")
                
                except Exception:
                    continue
            
            self.root.after(0, lambda: self.batch_unfollow_button.config(state="normal"))
            self.root.after(0, lambda: self.count_label.config(text=f"共 {len(self.tree.get_children())} 个关注"))
            self.root.after(0, lambda: self.update_status(f"✅ 完成！成功取消关注 {success_count} 个用户"))
            self.root.after(0, lambda: messagebox.showinfo("🎉 完成", f"成功取消关注 {success_count} 个用户"))
        
        thread = threading.Thread(target=unfollow_thread)
        thread.daemon = True
        thread.start()
    
    def export_list(self):
        selected_items = [item for item, checked in self.checked_items.items() if checked]
        if not selected_items:
            messagebox.showwarning("⚠️ 警告", "请先选择要导出的关注用户")
            return
        
        try:
            # 只导出重要的数据字段
            simplified_list = []
            for item_id in selected_items:
                # 从数据映射获取完整的用户数据
                user = self.item_data.get(item_id)
                if user:
                    simplified_user = {
                        '用户名': user.get('uname', '未知'),
                        'UID': user.get('mid', ''),
                        '关注时间': user.get('mtime_str', '未知'),
                        '关注时间戳': user.get('mtime', ''),
                        '签名': user.get('sign', '').strip() or '暂无签名',
                        '官方认证': user.get('official_verify', {}).get('desc', '') if user.get('official_verify') else '',
                        '头像链接': user.get('face', '')
                    }
                    simplified_list.append(simplified_user)
            
            localtime = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
            filename = f"bilibili_following_{localtime}_{len(simplified_list)}_users.json"
            # 将文件保存到应用程序目录
            file_path = os.path.join(get_app_dir(), filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(simplified_list, f, indent=2, ensure_ascii=False)
            
            messagebox.showinfo("🎉 成功", f"关注列表已导出到:\n{file_path}\n\n📊 已导出 {len(simplified_list)} 个用户的重要信息")
            self.update_status(f"📥 列表已导出到 {filename}")
        except Exception as e:
            messagebox.showerror("❌ 错误", f"导出失败：{str(e)}")
    
    def import_and_follow(self):
        """导入文件并显示选择界面"""
        # 选择文件
        file_path = filedialog.askopenfilename(
            title="选择要导入的关注列表文件",
            filetypes=[
                ("JSON文件", "*.json"),
                ("所有文件", "*.*")
            ],
            initialdir=get_app_dir()
        )
        
        if not file_path:
            return
        
        try:
            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                user_list = json.load(f)
            
            if not isinstance(user_list, list):
                messagebox.showerror("❌ 错误", "文件格式不正确，应该是包含用户列表的JSON数组")
                return
            
            if not user_list:
                messagebox.showerror("❌ 错误", "文件中没有用户数据")
                return
            
            # 解析用户数据
            parsed_users = self.parse_user_data(user_list)
            
            if not parsed_users:
                messagebox.showerror("❌ 错误", "文件中没有找到有效的用户数据")
                return
            
            # 打开选择界面
            self.show_import_selection_window(parsed_users, file_path)
            
        except json.JSONDecodeError:
            messagebox.showerror("❌ 错误", "文件不是有效的JSON格式")
        except Exception as e:
            messagebox.showerror("❌ 错误", f"读取文件失败：{str(e)}")
    
    def parse_user_data(self, user_list):
        """解析用户数据，提取关键信息"""
        parsed_users = []
        
        for user in user_list:
            user_info = {}
            
            # 检查是否是简化版格式（中文字段名）
            if 'UID' in user:
                user_info['uid'] = user.get('UID')
                user_info['username'] = user.get('用户名', '未知用户')
                user_info['signature'] = user.get('签名', '')
                user_info['follow_time'] = user.get('关注时间', '')
            
            # 检查是否是原始格式（英文字段名）
            elif 'mid' in user:
                user_info['uid'] = user.get('mid')
                user_info['username'] = user.get('uname', '未知用户')
                user_info['signature'] = user.get('sign', '')
                user_info['follow_time'] = user.get('mtime_format', '')
            
            else:
                continue  # 跳过格式不正确的条目
            
            # 确保UID是整数
            try:
                user_info['uid'] = int(user_info['uid'])
                parsed_users.append(user_info)
            except (ValueError, TypeError):
                continue  # 跳过UID无效的条目
        
        return parsed_users
    
    def show_import_selection_window(self, users_data, file_path):
        """显示导入选择窗口"""
        # 创建新窗口
        selection_window = tk.Toplevel(self.root)
        selection_window.title("📤 选择要关注的UP主")
        selection_window.geometry("1000x800")
        selection_window.minsize(900, 700)
        selection_window.configure(bg=self.colors['bg_light'])
        
        # 设置窗口图标和居中
        selection_window.transient(self.root)
        selection_window.grab_set()
        
        # 居中显示
        selection_window.update_idletasks()
        x = (selection_window.winfo_screenwidth() // 2) - (1000 // 2)
        y = (selection_window.winfo_screenheight() // 2) - (800 // 2)
        selection_window.geometry(f"1000x800+{x}+{y}")
        
        # 主容器
        main_frame = tk.Frame(selection_window, bg=self.colors['bg_light'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 标题
        title_frame = tk.Frame(main_frame, bg=self.colors['bg_light'])
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = tk.Label(title_frame,
                              text="📤 选择要关注的UP主",
                              font=("Microsoft YaHei UI", 18, "bold"),
                              fg=self.colors['primary'],
                              bg=self.colors['bg_light'])
        title_label.pack()
        
        subtitle_label = tk.Label(title_frame,
                                 text=f"从文件 {os.path.basename(file_path)} 中找到 {len(users_data)} 个UP主",
                                 font=("Microsoft YaHei UI", 10),
                                 fg=self.colors['text_secondary'],
                                 bg=self.colors['bg_light'])
        subtitle_label.pack(pady=(5, 0))
        
        # 工具栏
        toolbar_frame = tk.Frame(main_frame, bg=self.colors['bg_light'])
        toolbar_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 左侧按钮
        left_buttons = tk.Frame(toolbar_frame, bg=self.colors['bg_light'])
        left_buttons.pack(side=tk.LEFT)
        
        select_all_btn = tk.Button(left_buttons, text="全选",
                                  command=lambda: self.selection_select_all(selection_tree, users_data),
                                  bg='#F0F0F0',
                                  fg=self.colors['text_primary'],
                                  font=('Microsoft YaHei UI', 9),
                                  relief='flat',
                                  padx=15, pady=6,
                                  cursor='hand2',
                                  activebackground='#E0E0E0')
        select_all_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        select_none_btn = tk.Button(left_buttons, text="取消全选",
                                   command=lambda: self.selection_select_none(selection_tree),
                                   bg='#F0F0F0',
                                   fg=self.colors['text_primary'],
                                   font=('Microsoft YaHei UI', 9),
                                   relief='flat',
                                   padx=15, pady=6,
                                   cursor='hand2',
                                   activebackground='#E0E0E0')
        select_none_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 统计信息
        stats_label = tk.Label(toolbar_frame,
                              text="已选择: 0 个",
                              font=("Microsoft YaHei UI", 10),
                              fg=self.colors['text_secondary'],
                              bg=self.colors['bg_light'])
        stats_label.pack(side=tk.RIGHT)
        
        # 列表框架
        list_frame = ttk.LabelFrame(main_frame, text="  UP主列表  ", padding=15)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # 创建Treeview
        tree_frame = tk.Frame(list_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # 滚动条
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 树形视图
        selection_tree = ttk.Treeview(tree_frame,
                                     columns=("username", "uid", "signature", "follow_time"),
                                     show="tree headings",
                                     yscrollcommand=v_scrollbar.set,
                                     height=20)
        selection_tree.pack(fill=tk.BOTH, expand=True)
        
        v_scrollbar.config(command=selection_tree.yview)
        
        # 设置列标题和宽度
        selection_tree.heading("#0", text="选择", anchor=tk.W)
        selection_tree.heading("username", text="用户名", anchor=tk.W)
        selection_tree.heading("uid", text="UID", anchor=tk.W)
        selection_tree.heading("signature", text="签名", anchor=tk.W)
        selection_tree.heading("follow_time", text="关注时间", anchor=tk.W)
        
        selection_tree.column("#0", width=60, minwidth=60)
        selection_tree.column("username", width=150, minwidth=100)
        selection_tree.column("uid", width=100, minwidth=80)
        selection_tree.column("signature", width=300, minwidth=200)
        selection_tree.column("follow_time", width=150, minwidth=120)
        
        # 存储选中状态
        checked_users = {}
        
        # 填充数据
        for user in users_data:
            item_id = selection_tree.insert("", tk.END,
                                           text="☐",
                                           values=(user['username'],
                                                  user['uid'],
                                                  user['signature'][:50] + "..." if len(user['signature']) > 50 else user['signature'],
                                                  user['follow_time']))
            checked_users[item_id] = False
        
        # 点击事件处理
        def on_item_click(event):
            region = selection_tree.identify_region(event.x, event.y)
            item = selection_tree.identify_row(event.y)
            
            if item and region == "tree":
                # 切换选中状态
                checked_users[item] = not checked_users[item]
                
                if checked_users[item]:
                    selection_tree.item(item, text="☑")
                else:
                    selection_tree.item(item, text="☐")
                
                # 更新统计
                selected_count = sum(checked_users.values())
                stats_label.config(text=f"已选择: {selected_count} 个")
        
        selection_tree.bind("<Button-1>", on_item_click)
        
        # 底部按钮
        button_frame = tk.Frame(main_frame, bg=self.colors['bg_light'])
        button_frame.pack(fill=tk.X, pady=(15, 0))
        
        # 取消按钮
        cancel_btn = tk.Button(button_frame, text="❌ 取消",
                              command=selection_window.destroy,
                              bg='#F5F5F5',
                              fg=self.colors['text_primary'],
                              font=('Microsoft YaHei UI', 10),
                              relief='flat',
                              padx=20, pady=8,
                              cursor='hand2',
                              activebackground='#E8E8E8')
        cancel_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # 确认关注按钮
        confirm_btn = tk.Button(button_frame, text="✅ 确认关注",
                               command=lambda: self.confirm_import_selection(
                                   selection_window, selection_tree, users_data, checked_users, file_path),
                               bg=self.colors['success'],
                               fg='white',
                               font=('Microsoft YaHei UI', 10, 'bold'),
                               relief='flat',
                               padx=20, pady=8,
                               cursor='hand2',
                               activebackground='#389E0D')
        confirm_btn.pack(side=tk.RIGHT)
        
        # 存储引用以便在其他方法中使用
        self.selection_tree = selection_tree
        self.selection_stats_label = stats_label
        self.selection_checked_users = checked_users
    
    def selection_select_all(self, tree, users_data):
        """全选所有用户"""
        for item in self.selection_checked_users:
            self.selection_checked_users[item] = True
            tree.item(item, text="☑")
        
        self.selection_stats_label.config(text=f"已选择: {len(users_data)} 个")
    
    def selection_select_none(self, tree):
        """取消全选"""
        for item in self.selection_checked_users:
            self.selection_checked_users[item] = False
            tree.item(item, text="☐")
        
        self.selection_stats_label.config(text="已选择: 0 个")
    
    def confirm_import_selection(self, window, tree, users_data, checked_users, file_path):
        """确认导入选择的用户"""
        # 获取选中的用户
        selected_users = []
        for i, (item_id, is_checked) in enumerate(checked_users.items()):
            if is_checked:
                selected_users.append(users_data[i])
        
        if not selected_users:
            messagebox.showwarning("⚠️ 提示", "请至少选择一个要关注的UP主")
            return
        
        # 确认操作
        if not messagebox.askyesno("🔔 确认批量关注", 
                                  f"确定要关注选中的 {len(selected_users)} 个UP主吗？\n\n"
                                  f"⚠️ 此操作将会逐个关注这些用户\n"
                                  f"⏱️ 预计需要 {len(selected_users)//10 + 1}-{len(selected_users)//5 + 1} 分钟",
                                  icon="question"):
            return
        
        # 关闭选择窗口
        window.destroy()
        
        # 提取UID列表
        uids_to_follow = [user['uid'] for user in selected_users]
        
        # 开始批量关注
        self.start_batch_follow(uids_to_follow, file_path)
    
    def start_batch_follow(self, uids_to_follow, file_path):
        """开始批量关注操作"""
        if not self.api:
            messagebox.showerror("❌ 错误", "API未初始化，请先设置登录")
            return
            
        def follow_thread():
            self.root.after(0, lambda: self.import_follow_button.config(state="disabled"))
            self.root.after(0, lambda: self.update_status("🔄 正在批量关注用户..."))
            
            success_count = 0
            failed_count = 0
            total = len(uids_to_follow)
            
            for i, uid in enumerate(uids_to_follow):
                try:
                    self.root.after(0, lambda current=i+1, total=total: 
                                  self.update_status(f"🔄 正在关注用户 ({current}/{total})..."))
                    
                    if self.api and hasattr(self.api, "follow_user") and callable(getattr(self.api, "follow_user")):
                        if self.api.follow_user(uid):
                            success_count += 1
                        else:
                            failed_count += 1
                    else:
                        failed_count += 1
                    
                    # 避免操作过快
                    time.sleep(1.0)  # 固定延迟1秒
                    
                except Exception as e:
                    failed_count += 1
                    print(f"关注用户 {uid} 失败: {e}")  # 使用print替代logger
            
            self.root.after(0, lambda: self.import_follow_button.config(state="normal"))
            
            # 显示结果
            result_msg = f"🎉 批量关注完成！\n\n✅ 成功关注: {success_count} 个用户\n"
            if failed_count > 0:
                result_msg += f"❌ 失败: {failed_count} 个用户\n"
            result_msg += f"📁 源文件: {os.path.basename(file_path)}"
            
            self.root.after(0, lambda: messagebox.showinfo("🎉 完成", result_msg))
            self.root.after(0, lambda: self.update_status(f"✅ 批量关注完成！成功 {success_count} 个，失败 {failed_count} 个"))
            
            # 刷新关注列表
            if success_count > 0:
                self.root.after(2000, self.refresh_following)  # 2秒后自动刷新
        
        thread = threading.Thread(target=follow_thread)
        thread.daemon = True
        thread.start()
    
    def update_status(self, message):
        self.status_bar.config(text=message)
    
    def show_about(self):
        """显示关于对话框"""
        about_text = """
B站关注管理器 v1.1
Bilibili Follow Manager

🎬 现代化的B站关注管理工具

作者: 一懒众衫小 (Noeky)
GitHub: https://github.com/Noeky/bilibili-follow-manager
许可证: MIT License - 完全免费开源

Copyright © 2025 一懒众衫小 (Noeky)

✨ 功能特色:
• 自动登录和凭据保存
• 智能展示关注用户信息
• 批量取消关注操作
• 数据导出和导入功能

💝 如果这个项目对您有帮助，
请在GitHub上给个Star支持一下！
        """
        messagebox.showinfo("关于 B站关注管理器", about_text.strip())
        
    def on_tree_click(self, event):
        """处理树形视图的点击事件"""
        region = self.tree.identify_region(event.x, event.y)
        item = self.tree.identify_row(event.y)
        
        if not item:
            return
            
        if region == "tree":  # 只有点击在图标区域时才切换勾选状态
            # 切换选中状态
            self.toggle_check(item)
        # 其他区域的点击不处理，让Treeview默认的选择机制生效
    
    def toggle_check(self, item):
        """切换选中状态"""
        # 获取当前状态并切换
        is_checked = self.checked_items.get(item, False)
        self.checked_items[item] = not is_checked
        
        # 更新显示
        if self.checked_items[item]:
            self.tree.item(item, text="☑")
            # 如果点击选中，也添加到 Treeview 的 selection
            self.tree.selection_add(item)
        else:
            self.tree.item(item, text="☐")
            # 如果取消选中，从 selection 中移除
            self.tree.selection_remove(item)

def main():
    root = tk.Tk()
    app = BilibiliManagerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
