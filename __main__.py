import concurrent.futures
import tkinter as tk
import tkinter.messagebox as tmsg
from tkinter import filedialog
import customtkinter as ctk
import os
import time
import pyperclip
from yt_dlp import YoutubeDL 
from mimetypes import guess_type
from threading import Thread
import re
import shutil
import datetime
import urllib.request, urllib.error
import glob

DEFAULT_FONT = "游ゴシック"
DEFAULT_FONT_SIZE = 15
DEFAULT_FONT_HEIGHT = DEFAULT_FONT_SIZE * 2


class App(ctk.CTk):
    
    def __init__(self):
        super().__init__()

        self.titlefonts = (DEFAULT_FONT, 25, "bold")
        self.fonts = (DEFAULT_FONT, DEFAULT_FONT_SIZE)
        self.now_version = "0.0.2"

        # チェックボックスの状態を保存するリストを初期化
        self.download_filetype_check = [tk.StringVar(value="0") for _ in range(5)]
        self.download_path = tk.StringVar()
        self.download_url = tk.StringVar()
        self.realtime_progress = tk.StringVar()
        self.progress_finish_flag = tk.StringVar()
        self.playlist_download = tk.StringVar(value="0")
        self.ffmpeg_path = tk.StringVar()

        self.setup_form()

    def setup_form(self):
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.geometry("960x540")
        self.minsize(width=530, height=540)
        self.maxsize(width=1920, height=1040)
        self.title("Simple video downloader")

        self.grid_columnconfigure(0, weight=1)

        self.title = ctk.CTkLabel(self, text="Simple video downloader", font=self.titlefonts)
        self.title.grid(row=0, column=0, pady=(30,0), sticky="ew")
        self.title = ctk.CTkLabel(self, text=f"version {self.now_version}", font=self.fonts)
        self.title.grid(row=1, column=0, pady=(0,20), sticky="new")

        self.url_insert_frame = urlSettings(master=self, header_name="URLを入力", url_var=self.download_url)
        self.url_insert_frame.grid(row=2, column=0, padx=30, pady=(0, 6), sticky="new")

        self.path_open_frame = pathSettings(master=self, header_name="ダウンロード場所を入力", path_var=self.download_path)
        self.path_open_frame.grid(row=3, column=0, padx=30, pady=8, sticky="new")

        self.file_settings_frame = fileSettings(master=self, header_name="ファイル形式を選択", var_list=self.download_filetype_check)
        self.file_settings_frame.grid(row=4, column=0, padx=30, pady=8, sticky="new")

        self.start_button = ctk.CTkButton(self, text="ダウンロード", command=self.download_button, font=(DEFAULT_FONT, 20))
        self.start_button.grid(row=5, column=0, padx=30, pady=8, ipady=8, sticky="new")

        self.progress_bar = ctk.CTkProgressBar(self, width=300)
        self.progress_bar.grid(row=6, column=0, padx=30, pady=4, sticky="new")
        self.progress_bar.set(0)

        self.progress = ctk.CTkLabel(self, textvariable=str(self.realtime_progress), font=self.fonts)
        self.progress.grid(row=7, column=0, padx=30, pady=2, sticky="new")

    def download_button(self):
        self.create_thread()

    def create_thread(self):
        self.run_thread = Thread( target=self.method_in_a_thread )
        self.run_thread.start()
        self.export_log(f"create thread:{self.run_thread}")

    def method_in_a_thread(self):
        self.download_start()

    def download_start(self):
        self.export_log(f"download_start()")
        self.progress_finish_flag.set("false")
        selected_filetypes = [var.get() for var in self.download_filetype_check]
        selected_filetypes = [s for s in selected_filetypes if s != '0']
        download_path = self.path_open_frame.get_url()
        download_url = self.url_insert_frame.get_url()

        if not download_url:
            self.show_error("URLを入力してください！")
            self.export_log(f"url error")
            return

        if not download_path:
            self.show_error("ダウンロード場所を入力してください！")
            self.export_log(f"download path error")
            return

        if not selected_filetypes:
            self.show_error("ファイル形式を選択してください！")
            self.export_log(f"format error")
            return

        if os.path.isfile("ffmpeg.exe"):
            self.ffmpeg_path.set(os.path.realpath(os.path.abspath('ffmpeg.exe')))
        elif "ffmpeg" in os.environ['Path']:
            ffmpeg_path = [s for s in os.environ["Path"].split(";") if 'ffmpeg' in s]
            ffmpeg_path = ffmpeg_path[0] + "\\ffmpeg.exe"
            print(ffmpeg_path)
            self.ffmpeg_path.set(ffmpeg_path)
        else:
            self.realtime_progress.set("初回準備中...")
            url = 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl-shared.zip'
            dst_path = 'ffmpeg-master-latest-win64-gpl-shared.zip'
            urllib.request.urlretrieve(url, dst_path)
            shutil.unpack_archive(dst_path, 'ffmpeg_temp')
            shutil.move('ffmpeg_temp/ffmpeg-master-latest-win64-gpl-shared/bin/', 'ffmpeg/')
            os.remove('ffmpeg-master-latest-win64-gpl-shared.zip')
            shutil.rmtree('ffmpeg_temp/')
            self.ffmpeg_path.set(os.path.realpath(os.path.abspath('ffmpeg/ffmpeg.exe')))

            

        self.realtime_progress.set("準備中...")
        self.progress_bar.set(0)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(self.download_video, download_url, download_path, file) for file in selected_filetypes]
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                    self.export_log(f"try future.result()")
                except Exception as exc:
                    self.export_log(f"Exception occurred: {exc}")
                    print(f"Exception occurred: {exc}")

        self.realtime_progress.set("ダウンロード完了！")
        self.export_log(f"download progress finish")

    def progress_hook(self, d):
        if self.progress_finish_flag.get() == "true":
            return
        if d['status'] == 'downloading':
            percent_str = re.sub(r'\x1b\[[0-9;]*m', '', d['_percent_str'])
            percentage = float(percent_str.strip('%'))
            self.progress_bar.set(percentage / 100)
            self.realtime_progress.set("ダウンロード中...")
        elif d['status'] == 'finished':
            self.realtime_progress.set("仕上げ中...")
            self.progress_finish_flag.set("true")


    def download_video(self, url, path, file):
        playlist_download = self.url_insert_frame.get_checkbox()
        edited_url = url

        """
        
            self.export_log(f"remove list url")
            edited_url = edited_url.split("&list=")[0]"""

        mime_type, encoding = guess_type(f"example.{file}")
        ffmpeg_path = self.ffmpeg_path.get()
        option = {
            'outtmpl': os.path.join(path, '%(title)s.%(ext)s'),
            'progress_hooks': [self.progress_hook],
            'ffmpeg_location':ffmpeg_path
        }

        if playlist_download == "0":
            option['noplaylist'] = True
        else:
            option['noplaylist'] = False

        # ダウンロード先ディレクトリの存在を確認し、存在しない場合は作成する
        output_dir = os.path.dirname(option['outtmpl'])
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        if mime_type.startswith("audio"):
            self.export_log(f"audio format detect")
            option['format'] = 'bestaudio'
            option['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': file,
            }]
            with YoutubeDL(option) as ydl:
                ydl.download(edited_url)

        elif mime_type.startswith("video"):
            self.export_log(f"video format detect")
            with YoutubeDL(option) as ydl:
                self.export_log(f"get video info")
                info_dict = ydl.extract_info(edited_url, download=False)
                video_entries = []
                if 'entries' in info_dict:
                    self.export_log(f"entries in info")
                    for entry in info_dict['entries']:
                        video_entries.append(entry)
                else:
                    video_entries.append(info_dict)

                for video_entry in video_entries:
                    formats = video_entry.get('formats', [])
                    available_formats = set(fmt['ext'] for fmt in formats)

                    if file in available_formats:
                        option['format'] = f'bestvideo*[ext={file}]+bestaudio[ext=m4a]/best[ext={file}]'
                        self.export_log(f"formats available:{file}")
                    else:
                        option['format'] = f'bestvideo*+bestaudio/best'
                        option['postprocessors'] = [{
                            'key': 'FFmpegVideoConvertor',
                            'preferredformat': file
                        }]
                        self.export_log(f"formats not available, conert to:{file}")

                    try:
                        with YoutubeDL(option) as ydl:
                            self.export_log(f"try download {video_entry['webpage_url']}")
                            ydl.download([video_entry['webpage_url']])
                            video_file = ydl.prepare_filename(video_entry)

                        # 無効なファイル名をクリーンアップ
                        cleaned_file_name = re.sub(r'[<>:"/\\|?*]', '', os.path.basename(video_file))
                        cleaned_file_path = os.path.join(path, cleaned_file_name)
                        if video_file != cleaned_file_path:
                            shutil.move(video_file, cleaned_file_path)

                        current_time = time.time()
                        os.utime(cleaned_file_path, (current_time, current_time))
                    except Exception as e:
                        print(f"Exception occurred while downloading {video_entry['webpage_url']}: {e}")
                        self.export_log(f"Exception occurred while downloading {video_entry['webpage_url']}: {e}")

        if self.progress_finish_flag.get() == "true":
            self.realtime_progress.set("ダウンロード完了！")
        self.export_log(f"download_video() finish")



    def show_error(self, messages):
        tmsg.showerror("Error",messages)

    def export_log(self, log):
        f = open("log.txt", "a", encoding="utf-8")
        nowtime = datetime.datetime.now()
        nowtime = nowtime.strftime("%Y-%m-%d %H:%M:%S")
        
        f.write(f"[{nowtime}]:{log}\n")
        f.close


class urlSettings(ctk.CTkFrame):
    def __init__(self, *args, header_name="urlSettings", url_var=None, playlist_download=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fonts = (DEFAULT_FONT, DEFAULT_FONT_SIZE)
        self.header_name = header_name
        self.textbox_var = url_var
        self.playlist_download = playlist_download

        self.setup_form()

    def setup_form(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text=self.header_name, font=(DEFAULT_FONT, 11))
        self.label.grid(row=0, column=0, padx=13, pady=2, sticky="w")

        #1
        self.textbox = ctk.CTkEntry(master=self, placeholder_text="URLを入力してください", width=120, height=DEFAULT_FONT_HEIGHT * 1.15, font=self.fonts)
        self.textbox.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")

        self.button_select = ctk.CTkButton(master=self, height=DEFAULT_FONT_HEIGHT * 1.15, fg_color="transparent", hover_color=("#bcbcbc", "#474747"), border_width=2, text_color=("gray10", "#DCE4EE"), command=self.paste_button, text="ペースト", font=self.fonts)
        self.button_select.grid(row=1, column=1, padx=(10,2), pady=(0, 10))

        self.checkbox = ctk.CTkCheckBox(self, text="プレイリストとして\nダウンロード(非推奨)", border_width=2, checkbox_height=DEFAULT_FONT_SIZE * 1.5, checkbox_width=DEFAULT_FONT_SIZE * 1.5, variable=self.playlist_download, onvalue="1", offvalue="0", font=(DEFAULT_FONT, 12))
        self.checkbox.grid(row=1, column=2, padx=10, pady=(0, 10))

    def paste_button(self):
        clipboard = pyperclip.paste()
        self.textbox.delete(0, tk.END)
        self.textbox.insert(0, clipboard)

    def get_url(self):
        return self.textbox.get()
    def get_checkbox(self):
        return self.checkbox.get()

class pathSettings(ctk.CTkFrame):
    def __init__(self, *args, header_name="pathSettings", path_var=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fonts = (DEFAULT_FONT, DEFAULT_FONT_SIZE)
        self.header_name = header_name
        self.download_path = path_var

        self.setup_form()

    def setup_form(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text=self.header_name, font=(DEFAULT_FONT, 11))
        self.label.grid(row=0, column=0, padx=13, pady=2, sticky="w")

        self.textbox = ctk.CTkEntry(master=self, placeholder_text="ダウンロード場所を入力してください", width=120, height=DEFAULT_FONT_HEIGHT * 1.15, font=self.fonts)
        self.textbox.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")

        self.button_select = ctk.CTkButton(master=self, height=DEFAULT_FONT_HEIGHT * 1.15, fg_color="transparent", hover_color=("#bcbcbc", "#474747"), border_width=2, text_color=("gray10", "#DCE4EE"), command=self.open_folder_button, text="フォルダを選択", font=self.fonts)
        self.button_select.grid(row=1, column=1, padx=10, pady=(0, 10))

        self.button_select = ctk.CTkButton(master=self, height=DEFAULT_FONT_HEIGHT * 1.15, fg_color="transparent", hover_color=("#bcbcbc", "#474747"), border_width=2, text_color=("gray10", "#DCE4EE"), command=self.open_defaultfolder_button, text="デフォルトを使用", font=self.fonts)
        self.button_select.grid(row=1, column=2, padx=10, pady=(0, 10))

    def open_folder_button(self):
        user_folder = os.path.expanduser("~")
        download_path = os.path.join(user_folder, "Downloads")
        selected_path = filedialog.askdirectory(initialdir=download_path)
        if selected_path != "":
            self.textbox.delete(0, tk.END)
            self.textbox.insert(0, selected_path.replace("/", "\\") + '\\')

    def open_defaultfolder_button(self):
        user_folder = os.path.expanduser("~")
        download_path = os.path.join(user_folder, "Downloads")
        self.textbox.delete(0, tk.END)
        self.textbox.insert(0, download_path + '\\')

    def get_url(self):
        return self.textbox.get()


class fileSettings(ctk.CTkFrame):
    def __init__(self, *args, header_name="fileSettings", var_list=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fonts = (DEFAULT_FONT, DEFAULT_FONT_SIZE)
        self.header_name = header_name
        self.var_list = var_list

        self.setup_form()

    def setup_form(self):
        self.grid_rowconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text=self.header_name, font=(DEFAULT_FONT, 11))
        self.label.grid(row=0, column=0, padx=13, pady=2, sticky="w")

        self.checkbox1 = ctk.CTkCheckBox(self, text="mp4", border_width=2, checkbox_height=DEFAULT_FONT_SIZE * 1.5, checkbox_width=DEFAULT_FONT_SIZE * 1.5, variable=self.var_list[0], onvalue="mp4", offvalue="0", font=(DEFAULT_FONT, DEFAULT_FONT_SIZE))
        self.checkbox1.grid(row=1, column=0, padx=13, pady=(0, 10), sticky="w")

        self.checkbox2 = ctk.CTkCheckBox(self, text="mp3", border_width=2, checkbox_height=DEFAULT_FONT_SIZE * 1.5, checkbox_width=DEFAULT_FONT_SIZE * 1.5, variable=self.var_list[1], onvalue="mp3", offvalue="0", font=(DEFAULT_FONT, DEFAULT_FONT_SIZE))
        self.checkbox2.grid(row=1, column=1, padx=13, pady=(0, 10), sticky="w")

        self.checkbox2 = ctk.CTkCheckBox(self, text="wav", border_width=2, checkbox_height=DEFAULT_FONT_SIZE * 1.5, checkbox_width=DEFAULT_FONT_SIZE * 1.5, variable=self.var_list[2], onvalue="wav", offvalue="0", font=(DEFAULT_FONT, DEFAULT_FONT_SIZE))
        self.checkbox2.grid(row=1, column=2, padx=13, pady=(0, 10), sticky="w")

        self.checkbox4 = ctk.CTkCheckBox(self, text="webm", border_width=2, checkbox_height=DEFAULT_FONT_SIZE * 1.5, checkbox_width=DEFAULT_FONT_SIZE * 1.5, variable=self.var_list[3], onvalue="webm", offvalue="0", font=(DEFAULT_FONT, DEFAULT_FONT_SIZE))
        self.checkbox4.grid(row=1, column=3, padx=13, pady=(0, 10), sticky="w")

        self.checkbox5 = ctk.CTkCheckBox(self, text="m4a", border_width=2, checkbox_height=DEFAULT_FONT_SIZE * 1.5, checkbox_width=DEFAULT_FONT_SIZE * 1.5, variable=self.var_list[4], onvalue="m4a", offvalue="0", font=(DEFAULT_FONT, DEFAULT_FONT_SIZE))
        self.checkbox5.grid(row=1, column=4, padx=13, pady=(0, 10), sticky="w")


if __name__ == "__main__":
    app = App()
    app.mainloop()
