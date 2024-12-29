import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import os
from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+
import threading
from tkinter import font

class CommentApp:
    def __init__(self, root):
        self.root = root
        self.root.title("评论管理器")
        self.root.geometry("1600x800")  # 增加窗口宽度以适应新增的列

        # 应用ttk主题
        style = ttk.Style()
        style.theme_use('clam')

        # 设置默认字体
        default_font = font.nametofont("TkDefaultFont")
        default_font.configure(size=10)

        # 定义排序状态字典
        self.sort_order = {
            "User": False,
            "Content": False,
            "Time": False,
            "Replyer_Number": False,
            "Rating": False
        }

        # 定义评级排序顺序
        self.rating_order = {
            "A1": 1, "A2": 2,
            "B1": 3, "B2": 4, "B3": 5,
            "C1": 6, "C2": 7, "C3": 8,
            "D": 9
        }

        # 创建顶部框架用于按钮和搜索
        top_frame = tk.Frame(root)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        load_button = tk.Button(top_frame, text="加载CSV", command=self.load_csv)
        load_button.pack(side=tk.LEFT)

        export_txt_button = tk.Button(top_frame, text="导出TXT", command=self.export_txt)
        export_txt_button.pack(side=tk.LEFT, padx=5)

        export_csv_button = tk.Button(top_frame, text="导出CSV", command=self.export_csv)
        export_csv_button.pack(side=tk.LEFT, padx=5)

        refresh_button = tk.Button(top_frame, text="刷新", command=self.refresh_tree)
        refresh_button.pack(side=tk.LEFT, padx=5)

        exit_button = tk.Button(top_frame, text="退出", command=root.quit)
        exit_button.pack(side=tk.RIGHT)

        # 添加搜索功能
        search_label = tk.Label(top_frame, text="搜索:")
        search_label.pack(side=tk.LEFT, padx=(20, 5))

        self.search_entry = tk.Entry(top_frame)
        self.search_entry.pack(side=tk.LEFT, padx=5)

        search_button = tk.Button(top_frame, text="搜索", command=self.search_comments)
        search_button.pack(side=tk.LEFT, padx=5)

        # 创建进度条框架
        progress_frame = tk.Frame(root)
        progress_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0, 10))

        self.progress = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X)
        self.progress.stop()  # 初始时停止进度条

        # 创建Treeview和滚动条
        tree_frame = tk.Frame(root)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tree = ttk.Treeview(tree_frame, columns=("User", "Content", "Time", "Replyer_Number", "Rating"), show='tree headings')
        self.tree.heading("#0", text="Comment ID")
        self.tree.heading("User", text="用户昵称")
        self.tree.heading("Content", text="内容")
        self.tree.heading("Time", text="创建时间")
        self.tree.heading("Replyer_Number", text="回复者数量")
        self.tree.heading("Rating", text="评级")

        self.tree.column("#0", width=150, anchor='w')
        self.tree.column("User", width=150, anchor='w')
        self.tree.column("Content", width=800, anchor='w')  # 增加内容列宽度
        self.tree.column("Time", width=150, anchor='w')
        self.tree.column("Replyer_Number", width=120, anchor='center')
        self.tree.column("Rating", width=100, anchor='center')

        # 添加垂直滚动条
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y')

        # 添加水平滚动条
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(xscrollcommand=hsb.set)
        hsb.pack(side='bottom', fill='x')

        self.tree.pack(fill=tk.BOTH, expand=True)

        # 绑定列标题点击事件用于排序
        for col in ("User", "Content", "Time", "Replyer_Number", "Rating"):
            self.tree.heading(col, text=col, command=lambda _col=col: self.sort_column(_col))

        # 初始化数据结构
        self.comments = {}
        self.replies = {}
        self.df = None
        self.filtered_comments = {}
        self.filtered_replies = {}
        self.up_host_id = None  # 用于标识Up主的user_id

    def load_csv(self):
        file_path = filedialog.askopenfilename(
            title="选择CSV文件",
            filetypes=(("CSV Files", "*.csv"), ("All Files", "*.*"))
        )

        if not file_path:
            return

        # 启动进度条
        self.start_progress()

        # 启动一个新线程加载和处理CSV
        threading.Thread(target=self.load_csv_thread, args=(file_path,)).start()

    def load_csv_thread(self, file_path):
        try:
            encoding = 'utf-8'  # 默认编码
            self.df = pd.read_csv(file_path, dtype=str, encoding=encoding)
            self.process_data()
            self.populate_tree()
            # 停止进度条并显示成功消息（通过主线程）
            self.root.after(0, self.load_success, file_path)
        except UnicodeDecodeError:
            try:
                encoding = 'gbk'  # 尝试其他常用编码
                self.df = pd.read_csv(file_path, dtype=str, encoding=encoding)
                self.process_data()
                self.populate_tree()
                self.root.after(0, self.load_success, file_path)
            except Exception as e:
                self.root.after(0, self.load_error, e)
        except Exception as e:
            self.root.after(0, self.load_error, e)

    def load_success(self, file_path):
        self.stop_progress()
        messagebox.showinfo("成功", f"成功加载文件: {os.path.basename(file_path)}")

    def load_error(self, error):
        self.stop_progress()
        messagebox.showerror("错误", f"加载文件失败: {error}")

    def start_progress(self):
        self.progress.start(10)  # 每10毫秒移动一次
        self.progress.pack()  # 确保进度条可见

    def stop_progress(self):
        self.progress.stop()
        self.progress.pack_forget()  # 隐藏进度条

    def process_data(self):
        if self.df is None:
            return

        # 确保必要的列存在
        required_columns = [
            "comment_id", "parent_comment_id", "create_time",
            "video_id", "content", "user_id", "nickname",
            "avatar", "sub_comment_count", "last_modify_ts"
        ]
        missing_columns = [col for col in required_columns if col not in self.df.columns]
        if missing_columns:
            raise ValueError(f"缺少必要的列: {', '.join(missing_columns)}")

        # 转换create_time为整数
        self.df["create_time"] = pd.to_numeric(self.df["create_time"], errors='coerce')
        self.df = self.df.dropna(subset=["create_time"])
        self.df["create_time"] = self.df["create_time"].astype(int)

        # 构建评论和回复的字典
        self.comments = {}
        self.replies = {}

        missing_video_id = []

        for idx, row in self.df.iterrows():
            comment_id = row["comment_id"]
            if comment_id in self.comments:
                # 处理重复的comment_id
                comment_id = f"{comment_id}_{idx}"
            parent_id = row["parent_comment_id"]
            video_id = row.get("video_id", "").strip()

            if not video_id:
                missing_video_id.append(comment_id)
                # 可以选择跳过这条评论或设置一个默认值
                # 这里我们设置为 "N/A"
                video_id = "N/A"

            comment = {
                "comment_id": comment_id,
                "parent_comment_id": parent_id,
                "create_time": row["create_time"],
                "content": row["content"],
                "nickname": row["nickname"],
                "user_id": row["user_id"],
                "avatar": row["avatar"],
                "sub_comment_count": row["sub_comment_count"],
                "last_modify_ts": row["last_modify_ts"],
                "rating": ""  # 初始化评级（小写）
            }
            # 添加video_id
            comment["video_id"] = video_id

            self.comments[comment_id] = comment
            if parent_id not in self.replies:
                self.replies[parent_id] = []
            self.replies[parent_id].append(comment)

        # 如果有缺失video_id的评论，提醒用户
        if missing_video_id:
            message = f"以下评论缺少 'video_id'，已设置为 'N/A':\n" + ", ".join(missing_video_id)
            messagebox.showwarning("警告", message)

        # 对每个回复列表按create_time排序
        for parent_id in self.replies:
            self.replies[parent_id].sort(key=lambda x: x["create_time"])

        # 确定Up主的user_id（假设第一个顶级评论来自Up主）
        top_level_comments = [c for c in self.comments.values() if c["parent_comment_id"] not in self.comments]
        if top_level_comments:
            self.up_host_id = top_level_comments[0]["user_id"]
        else:
            self.up_host_id = None

        # 计算评级
        for comment in top_level_comments:
            self.assign_rating(comment)

        # 处理二级及更深层级的评论
        for comment in self.comments.values():
            if comment["parent_comment_id"] in self.comments:
                self.assign_rating(comment)

    def assign_rating(self, comment):
        # 如果评论来自Up主
        if comment["user_id"] == self.up_host_id:
            # 判断是否为顶级评论
            if comment["parent_comment_id"] not in self.comments:
                comment["rating"] = "A1"
            else:
                comment["rating"] = "A2"
            return

        # 获取二级回复
        second_replies = self.replies.get(comment["comment_id"], [])
        count_second = len(second_replies)

        # 获取三级回复
        count_third = sum(len(self.replies.get(reply["comment_id"], [])) for reply in second_replies)

        # 根据评级标准分配评级
        if count_second == 0:
            comment["rating"] = "D"
        elif 1 <= count_second < 10:
            if count_third > 0:
                comment["rating"] = "B1"
            else:
                comment["rating"] = "C1"
        elif 10 <= count_second <= 100:
            if count_third >= 10:
                comment["rating"] = "B2"
            else:
                comment["rating"] = "C2"
        elif count_second > 100:
            if count_third >= 100:
                comment["rating"] = "B3"
            else:
                comment["rating"] = "C3"

    def populate_tree(self, filtered=False):
        # 清空现有的Treeview
        for item in self.tree.get_children():
            self.tree.delete(item)

        if filtered:
            top_level_comments = [
                comment for comment in self.filtered_comments.values()
                if comment["parent_comment_id"] not in self.filtered_comments
            ]
        else:
            top_level_comments = [
                comment for comment in self.comments.values()
                if comment["parent_comment_id"] not in self.comments
            ]

        # 按create_time排序顶级评论
        top_level_comments.sort(key=lambda x: x["create_time"], reverse=self.sort_order.get("Time", False))

        for comment in top_level_comments:
            time_str = self.convert_timestamp(comment["create_time"])
            replyer_number = len(self.replies.get(comment["comment_id"], [])) if not filtered else len(self.filtered_replies.get(comment["comment_id"], []))
            node = self.tree.insert(
                "",
                "end",
                text=comment["comment_id"],
                values=(comment["nickname"], comment["content"], time_str, replyer_number, comment["rating"])
            )
            self.insert_replies(node, comment["comment_id"], filtered)

    def insert_replies(self, parent_node, parent_id, filtered=False):
        replies = self.replies.get(parent_id, []) if not filtered else self.filtered_replies.get(parent_id, [])
        for idx, reply in enumerate(replies, start=1):
            time_str = self.convert_timestamp(reply["create_time"])
            replyer_number = len(self.replies.get(reply["comment_id"], [])) if not filtered else len(self.filtered_replies.get(reply["comment_id"], []))
            node = self.tree.insert(
                parent_node,
                "end",
                text=reply["comment_id"],
                values=(reply["nickname"], reply["content"], time_str, replyer_number, reply["rating"])
            )
            # 递归插入更深层的回复
            self.insert_replies(node, reply["comment_id"], filtered)

    def convert_timestamp(self, ts):
        try:
            if ts < 0 or ts > 1e12:
                return "无效时间"
            if ts > 1e12:  # 毫秒级别
                ts = ts / 1000
            # 转换为北京时间
            beijing_tz = ZoneInfo("Asia/Shanghai")
            dt = datetime.fromtimestamp(ts, tz=beijing_tz)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            return f"未知时间 ({e})"

    def refresh_tree(self):
        if self.df is not None:
            # 启动进度条
            self.start_progress()
            # 启动一个新线程处理刷新
            threading.Thread(target=self.refresh_tree_thread).start()
        else:
            messagebox.showwarning("警告", "没有加载任何CSV文件。")

    def refresh_tree_thread(self):
        try:
            self.process_data()
            self.populate_tree()
            self.root.after(0, self.refresh_success)
        except Exception as e:
            self.root.after(0, self.refresh_error, e)

    def refresh_success(self):
        self.stop_progress()
        messagebox.showinfo("刷新", "评论数据已刷新。")

    def refresh_error(self, error):
        self.stop_progress()
        messagebox.showerror("错误", f"刷新失败: {error}")

    def export_txt(self):
        if self.df is None:
            messagebox.showwarning("警告", "没有加载任何CSV文件。")
            return

        # 选择保存位置
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=(("Text Files", "*.txt"), ("All Files", "*.*")),
            title="保存为TXT文件"
        )

        if not file_path:
            return

        # 启动进度条
        self.start_progress()

        # 启动一个新线程导出
        threading.Thread(target=self.export_txt_thread, args=(file_path,)).start()

    def export_txt_thread(self, file_path):
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # 找到顶级评论
                top_level_comments = [
                    comment for comment in self.comments.values()
                    if comment["parent_comment_id"] not in self.comments
                ]

                # 按create_time排序顶级评论
                top_level_comments.sort(key=lambda x: x["create_time"], reverse=self.sort_order.get("Time", False))

                for comment in top_level_comments:
                    f.write("{\n")
                    f.write(f"    main_post: {comment['comment_id']}\n")
                    f.write(f"    time: {self.convert_timestamp(comment['create_time'])}\n")
                    f.write(f"    username: {comment['nickname']} ({comment['user_id']})\n")
                    replyer_number = len(self.replies.get(comment["comment_id"], []))
                    f.write(f"    replyer_number: {replyer_number}\n")
                    f.write(f"    rating: {comment['rating']}\n")
                    f.write(f"    content: {comment['content']}\n")

                    # 插入回复
                    self.write_replies(f, comment["comment_id"], indent_level=1, replyer_count=1)

                    f.write("}\n\n")

            # 停止进度条并显示成功消息（通过主线程）
            self.root.after(0, self.export_success, file_path)
        except Exception as e:
            self.root.after(0, self.export_error, e)

    def export_success(self, file_path):
        self.stop_progress()
        messagebox.showinfo("成功", f"成功导出TXT文件到: {file_path}")

    def export_error(self, error):
        self.stop_progress()
        messagebox.showerror("错误", f"导出TXT文件失败: {error}")

    def export_csv(self):
        if self.df is None:
            messagebox.showwarning("警告", "没有加载任何CSV文件。")
            return

        # 选择保存位置
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=(("CSV Files", "*.csv"), ("All Files", "*.*")),
            title="保存为CSV文件"
        )

        if not file_path:
            return

        # 启动进度条
        self.start_progress()

        # 启动一个新线程导出
        threading.Thread(target=self.export_csv_thread, args=(file_path,)).start()

    def export_csv_thread(self, file_path):
        try:
            # 准备导出数据
            data_to_export = []

            for comment in self.comments.values():
                data = {
                    "comment_id": comment.get("comment_id", ""),
                    "parent_comment_id": comment.get("parent_comment_id", ""),
                    "create_time": self.convert_timestamp(comment.get("create_time", 0)),
                    "video_id": comment.get("video_id", "N/A"),  # 使用get避免KeyError
                    "content": comment.get("content", ""),
                    "user_id": comment.get("user_id", ""),
                    "nickname": comment.get("nickname", ""),
                    "avatar": comment.get("avatar", ""),
                    "sub_comment_count": comment.get("sub_comment_count", ""),
                    "last_modify_ts": comment.get("last_modify_ts", ""),
                    "rating": comment.get("rating", "")
                }
                data_to_export.append(data)

            # 将数据转换为DataFrame
            export_df = pd.DataFrame(data_to_export)

            # 导出为CSV
            export_df.to_csv(file_path, index=False, encoding='utf-8-sig')

            # 停止进度条并显示成功消息（通过主线程）
            self.root.after(0, self.export_csv_success, file_path)
        except Exception as e:
            self.root.after(0, self.export_csv_error, e)

    def export_csv_success(self, file_path):
        self.stop_progress()
        messagebox.showinfo("成功", f"成功导出CSV文件到: {file_path}")

    def export_csv_error(self, error):
        self.stop_progress()
        messagebox.showerror("错误", f"导出CSV文件失败: {error}")

    def write_replies(self, file, parent_id, indent_level, replyer_count):
        replies = self.replies.get(parent_id, [])
        for idx, reply in enumerate(replies, start=1):
            indent = "    " * (indent_level + 1)
            file.write(f"{indent}replyer{idx}:\n")
            file.write(f"{indent}    time: {self.convert_timestamp(reply['create_time'])}\n")
            file.write(f"{indent}    username: {reply['nickname']} ({reply['user_id']})\n")
            replyer_number = len(self.replies.get(reply["comment_id"], []))
            file.write(f"{indent}    replyer_number: {replyer_number}\n")
            file.write(f"{indent}    rating: {reply['rating']}\n")
            file.write(f"{indent}    content: {reply['content']}\n")
            # 递归写入更深层的回复
            self.write_replies(file, reply["comment_id"], indent_level + 1, replyer_count=1)

    def search_comments(self):
        query = self.search_entry.get().strip().lower()
        if not query:
            self.populate_tree()
            return

        # 过滤符合条件的评论
        self.filtered_comments = {cid: comment for cid, comment in self.comments.items()
                                  if query in comment['nickname'].lower() or query in comment['content'].lower()}
        self.filtered_replies = {}
        for parent_id, replies in self.replies.items():
            filtered = [reply for reply in replies if reply['comment_id'] in self.filtered_comments]
            if filtered:
                self.filtered_replies[parent_id] = filtered
        self.populate_tree(filtered=True)

    def sort_column(self, col):
        # 切换排序方向
        self.sort_order[col] = not self.sort_order[col]

        # 更新列标题以显示箭头，并清除其他列的箭头
        for column in ("User", "Content", "Time", "Replyer_Number", "Rating"):
            if column == col:
                arrow = "▲" if not self.sort_order[col] else "▼"
                self.tree.heading(column, text=f"{column} {arrow}", command=lambda _col=column: self.sort_column(_col))
            else:
                self.tree.heading(column, text=column, command=lambda _col=column: self.sort_column(_col))

        # 获取所有顶级评论
        top_level_comments = [c for c in self.comments.values() if c["parent_comment_id"] not in self.comments]

        # 根据列类型进行排序
        if col == "Time":
            sorted_comments = sorted(top_level_comments, key=lambda x: x["create_time"], reverse=self.sort_order[col])
        elif col == "Replyer_Number":
            sorted_comments = sorted(top_level_comments, key=lambda x: int(x["Replyer_Number"]) if x["Replyer_Number"].isdigit() else 0, reverse=self.sort_order[col])
        elif col == "Rating":
            sorted_comments = sorted(top_level_comments, key=lambda x: self.rating_order.get(x["rating"], 100), reverse=self.sort_order[col])
        else:
            sorted_comments = sorted(top_level_comments, key=lambda x: x[col].lower() if isinstance(x[col], str) else x[col], reverse=self.sort_order[col])

        # 清空Treeview
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 插入排序后的顶级评论
        for comment in sorted_comments:
            time_str = self.convert_timestamp(comment["create_time"])
            replyer_number = len(self.replies.get(comment["comment_id"], [])) if not self.filtered_comments else len(self.filtered_replies.get(comment["comment_id"], []))
            node = self.tree.insert(
                "",
                "end",
                text=comment["comment_id"],
                values=(comment["nickname"], comment["content"], time_str, replyer_number, comment["rating"])
            )
            self.insert_replies(node, comment["comment_id"], self.filtered_comments)

def main():
    root = tk.Tk()
    app = CommentApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
