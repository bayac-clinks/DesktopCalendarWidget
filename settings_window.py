from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QLabel, QSpinBox, 
    QPushButton, QFontComboBox, QComboBox, QColorDialog, QDialogButtonBox,
    QGroupBox
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Signal, QSize
from config import config

class SettingsWindow(QDialog):
    settings_changed = Signal()

    def __init__(self, gcal_service, parent=None):
        super().__init__(parent)
        self.gcal_service = gcal_service
        self.setWindowTitle("設定")
        self.setMinimumWidth(450)

        main_layout = QVBoxLayout(self)

        appearance_group = QGroupBox("外観")
        appearance_layout = QGridLayout()
        appearance_layout.addWidget(QLabel("ウィンドウ幅:"), 0, 0); self.width_spin = QSpinBox(); self.width_spin.setRange(200, 3840); self.width_spin.setSuffix(" px"); appearance_layout.addWidget(self.width_spin, 0, 1)
        appearance_layout.addWidget(QLabel("ウィンドウ高さ:"), 1, 0); self.height_spin = QSpinBox(); self.height_spin.setRange(100, 2160); self.height_spin.setSuffix(" px"); appearance_layout.addWidget(self.height_spin, 1, 1)
        appearance_layout.addWidget(QLabel("角の丸み:"), 2, 0); self.radius_spin = QSpinBox(); self.radius_spin.setRange(0, 100); self.radius_spin.setSuffix(" px"); appearance_layout.addWidget(self.radius_spin, 2, 1)
        appearance_layout.addWidget(QLabel("背景色:"), 3, 0); self.bg_color_button = QPushButton("色を選択"); self.bg_color_button.clicked.connect(self.select_bg_color); appearance_layout.addWidget(self.bg_color_button, 3, 1)
        appearance_group.setLayout(appearance_layout); main_layout.addWidget(appearance_group)
        
        font_group = QGroupBox("フォントと色")
        font_layout = QGridLayout()
        font_layout.addWidget(QLabel("日付フォント:"), 0, 0); self.day_font_combo = QFontComboBox(); font_layout.addWidget(self.day_font_combo, 0, 1); self.day_font_size_spin = QSpinBox(); self.day_font_size_spin.setRange(8, 72); font_layout.addWidget(self.day_font_size_spin, 0, 2)
        font_layout.addWidget(QLabel("予定フォント:"), 1, 0); self.schedule_font_combo = QFontComboBox(); font_layout.addWidget(self.schedule_font_combo, 1, 1); self.schedule_font_size_spin = QSpinBox(); self.schedule_font_size_spin.setRange(8, 72); font_layout.addWidget(self.schedule_font_size_spin, 1, 2)
        font_layout.addWidget(QLabel("日付 文字色:"), 2, 0); self.day_color_button = QPushButton("色を選択"); self.day_color_button.clicked.connect(self.select_day_color); font_layout.addWidget(self.day_color_button, 2, 1)
        font_layout.addWidget(QLabel("予定 文字色:"), 3, 0); self.schedule_color_button = QPushButton("色を選択"); self.schedule_color_button.clicked.connect(self.select_schedule_color); font_layout.addWidget(self.schedule_color_button, 3, 1)
        font_group.setLayout(font_layout); main_layout.addWidget(font_group)
        
        calendar_group = QGroupBox("カレンダーと動作")
        calendar_layout = QGridLayout()
        calendar_layout.addWidget(QLabel("取得期間:"), 0, 0); self.fetch_days_combo = QComboBox(); self.fetch_days_combo.addItems(["1週間", "2週間", "3週間", "1ヶ月"]); self.fetch_days_map = [7, 14, 21, 30]; calendar_layout.addWidget(self.fetch_days_combo, 0, 1)
        calendar_layout.addWidget(QLabel("対象カレンダー:"), 1, 0); self.calendar_combo = QComboBox(); self.calendar_combo.setMinimumWidth(200); self.load_calendar_list(); calendar_layout.addWidget(self.calendar_combo, 1, 1)
        calendar_layout.addWidget(QLabel("表示切替の間隔:"), 2, 0); self.interval_spin = QSpinBox(); self.interval_spin.setRange(3, 300); self.interval_spin.setSuffix(" 秒"); calendar_layout.addWidget(self.interval_spin, 2, 1)
        calendar_group.setLayout(calendar_layout); main_layout.addWidget(calendar_group)

        # --- OK / キャンセルボタン ---
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply)
        # RestoreDefaultsボタンは標準セットにないので、別途追加します
        restore_button = self.button_box.addButton("初期設定に戻す", QDialogButtonBox.ResetRole)

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.Apply).clicked.connect(self.apply_settings)
        # restore_buttonのクリックイベントに接続します
        restore_button.clicked.connect(self.restore_defaults)

        # ボタンのテキストを日本語に変更
        self.button_box.button(QDialogButtonBox.Ok).setText("OK") # OKボタンも念のため
        self.button_box.button(QDialogButtonBox.Cancel).setText("キャンセル")
        self.button_box.button(QDialogButtonBox.Apply).setText("適用")
        
        main_layout.addWidget(self.button_box)

        self.load_settings()
    
    def _update_color_button_style(self, button, color):
        """ボタンの背景色と文字色を、見やすいように更新する"""
        button.setStyleSheet(f"background-color: {color.name()}; color: {'black' if color.lightness() > 127 else 'white'};")

    def select_bg_color(self):
        color = QColorDialog.getColor(self.bg_color, self)
        if color.isValid(): self.bg_color = color; self._update_color_button_style(self.bg_color_button, color)

    def select_day_color(self):
        color = QColorDialog.getColor(self.day_color, self)
        if color.isValid(): self.day_color = color; self._update_color_button_style(self.day_color_button, color)

    def select_schedule_color(self):
        color = QColorDialog.getColor(self.schedule_color, self)
        if color.isValid(): self.schedule_color = color; self._update_color_button_style(self.schedule_color_button, color)
            
    def load_calendar_list(self):
        import google_auth
        calendars = google_auth.get_calendar_list(self.gcal_service)
        self.calendar_combo.clear()

        # 除外したいカレンダーのIDを定義
        JAPANESE_HOLIDAY_CALENDAR_ID = 'ja.japanese#holiday@group.v.calendar.google.com'

        if calendars:
            for cal in calendars:
                cal_id = cal.get('id')

                # カレンダーIDが祝日カレンダーのものでなければ、リストに追加する
                if cal_id != JAPANESE_HOLIDAY_CALENDAR_ID:
                    summary = cal.get('summary')
                    self.calendar_combo.addItem(summary, cal_id)

    def load_settings(self):
        size = config.get_window_size(); self.width_spin.setValue(size.width()); self.height_spin.setValue(size.height())
        self.bg_color = config.get_background_color(); self._update_color_button_style(self.bg_color_button, self.bg_color)
        self.radius_spin.setValue(config.get_border_radius())
        day_font = config.get_day_font(); self.day_font_combo.setCurrentFont(day_font); self.day_font_size_spin.setValue(day_font.pointSize())
        schedule_font = config.get_schedule_font(); self.schedule_font_combo.setCurrentFont(schedule_font); self.schedule_font_size_spin.setValue(schedule_font.pointSize())
        self.day_color = config.get_day_font_color(); self._update_color_button_style(self.day_color_button, self.day_color)
        self.schedule_color = config.get_schedule_font_color(); self._update_color_button_style(self.schedule_color_button, self.schedule_color)
        
        fetch_days = config.get_fetch_days()
        if fetch_days in self.fetch_days_map: self.fetch_days_combo.setCurrentIndex(self.fetch_days_map.index(fetch_days))

        # calendar_idを元に、コンボボックスのインデックスを検索して設定
        calendar_id = config.get_calendar_id()
        index = self.calendar_combo.findData(calendar_id)
        if index != -1:  # IDが見つかった場合のみ設定
            self.calendar_combo.setCurrentIndex(index)
        
        self.interval_spin.setValue(config.get_animation_interval())

    def apply_settings(self):
        config.set_window_size(QSize(self.width_spin.value(), self.height_spin.value()))
        config.set_background_color(self.bg_color); config.set_border_radius(self.radius_spin.value())
        day_font = self.day_font_combo.currentFont(); day_font.setPointSize(self.day_font_size_spin.value()); config.set_day_font(day_font)
        schedule_font = self.schedule_font_combo.currentFont(); schedule_font.setPointSize(self.schedule_font_size_spin.value()); config.set_schedule_font(schedule_font)
        config.set_day_font_color(self.day_color)
        config.set_schedule_font_color(self.schedule_color)
        config.set_fetch_days(self.fetch_days_map[self.fetch_days_combo.currentIndex()])
        config.set_calendar_id(self.calendar_combo.currentData())
        config.set_animation_interval(self.interval_spin.value())
        self.settings_changed.emit()

    def accept(self):
        self.apply_settings(); super().accept()

    def restore_defaults(self):
        """設定をリセットし、UIに反映、メインウィンドウにも即時適用する"""
        config.reset_to_defaults()
        self.load_settings()
        self.apply_settings()
