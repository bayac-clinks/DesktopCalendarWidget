import os
import sys
from PySide6.QtCore import QSettings, QCoreApplication, QSize, QSettings # QSettings.IniFormat を使うために QSettings を明示的にインポート
from PySide6.QtGui import QColor, QFont

# ▼▼▼ パス解決のヘルパー関数をここに移動 ▼▼▼
def get_writable_path(filename):
    """ exe実行時はexeの隣に、スクリプト実行時はスクリプトの隣にファイルを書き込むためのパスを取得 """
    if getattr(sys, 'frozen', False):
        # exe実行時のパス (sys.executable は exe のフルパス)
        base_path = os.path.dirname(sys.executable)
    else:
        # スクリプト実行時のパス
        base_path = os.path.abspath(".")
    return os.path.join(base_path, filename)

# アプリケーションの情報を設定
QCoreApplication.setOrganizationName("MyCompany")
QCoreApplication.setApplicationName("DesktopCalendarWidget")

class Config:
    def __init__(self):
        # ▼▼▼ QSettingsの初期化方法を変更 ▼▼▼
        # self.settings = QSettings() # 以前のコードを削除

        # settings.ini ファイルのパスを取得
        settings_path = get_writable_path("settings.ini")
        # INIファイル形式で、指定したパスのファイルを読み書きするように設定
        self.settings = QSettings(settings_path, QSettings.IniFormat)
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

    def get(self, key, default_value):
        # QSettingsがファイルから読み込むので、この部分は変更不要
        return self.settings.value(key, default_value)

    def set(self, key, value):
        # QSettingsがファイルに書き込むので、この部分も変更不要
        self.settings.setValue(key, value)
        
    def reset_to_defaults(self):
        """保存されているすべての設定を削除し、デフォルト状態に戻す"""
        self.settings.clear()
        # ファイルから削除されたことを即座に反映
        self.settings.sync()

    # --- 個別の設定項目 (これ以降の get/set メソッドは一切変更不要) ---
    def get_window_size(self): return self.get("window/size", QSize(800, 220))
    def set_window_size(self, size): self.set("window/size", size)
    def get_background_color(self): return self.get("style/background_color", QColor(30, 30, 30, 180))
    def set_background_color(self, color): self.set("style/background_color", color)
    def get_border_color(self): return self.get("style/border_color", QColor(80, 80, 80, 220))
    def set_border_color(self, color): self.set("style/border_color", color)
    def get_border_radius(self): return int(self.get("style/border_radius", 15))
    def set_border_radius(self, radius): self.set("style/border_radius", radius)
    def get_day_font(self):
        default_font = QFont("Yu Gothic UI", 20); default_font.setBold(True)
        font_str = self.get("font/day_font", default_font.toString()); font = QFont(); font.fromString(font_str); return font
    def set_day_font(self, font): self.set("font/day_font", font.toString())
    def get_schedule_font(self):
        default_font = QFont("Yu Gothic UI", 12)
        font_str = self.get("font/schedule_font", default_font.toString()); font = QFont(); font.fromString(font_str); return font
    def set_schedule_font(self, font): self.set("font/schedule_font", font.toString())
    def get_day_font_color(self): return self.get("font/day_color", QColor("#FFFFFF"))
    def set_day_font_color(self, color): self.set("font/day_color", color)
    def get_schedule_font_color(self): return self.get("font/schedule_color", QColor("#FFFFFF"))
    def set_schedule_font_color(self, color): self.set("font/schedule_color", color)
    def get_animation_interval(self): return int(self.get("animation/interval_sec", 10))
    def set_animation_interval(self, seconds): self.set("animation/interval_sec", seconds)
    def get_fetch_days(self): return int(self.get("calendar/fetch_days", 7))
    def set_fetch_days(self, days): self.set("calendar/fetch_days", days)
    def get_calendar_id(self): return self.get("calendar/id", "primary")
    def set_calendar_id(self, calendar_id): self.set("calendar/id", calendar_id)

config = Config()