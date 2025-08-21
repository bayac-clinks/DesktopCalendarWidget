import sys
import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QPushButton, QStyle, QFrame, QLabel, QSizePolicy
)
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QFont
from PySide6.QtCore import (
    Qt, QRectF, QSize, Signal, QTimer, QPropertyAnimation, 
    QPoint, QEasingCurve, QParallelAnimationGroup
)

import google_auth
from config import config # config.pyをインポート
from settings_window import SettingsWindow # settings_window.pyをインポート

class TitleBar(QFrame):
    settings_requested = Signal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setFixedHeight(35)
        self.setStyleSheet("background-color: transparent;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.addStretch()
        button_style = "QPushButton { background-color: transparent; border: none; padding: 5px; } QPushButton:hover { background-color: rgba(255, 255, 255, 30); border-radius: 4px; } QPushButton:pressed { background-color: rgba(255, 255, 255, 20); }"
        self.settings_button = QPushButton()
        self.settings_button.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.settings_button.setStyleSheet(button_style)
        self.settings_button.setToolTip("設定")
        self.settings_button.clicked.connect(self.settings_requested.emit)
        layout.addWidget(self.settings_button)
        self.minimize_button = QPushButton()
        self.minimize_button.setIcon(self.style().standardIcon(QStyle.SP_TitleBarMinButton))
        self.minimize_button.setStyleSheet(button_style)
        self.minimize_button.setToolTip("最小化")
        self.minimize_button.clicked.connect(self.parent_window.showMinimized)
        layout.addWidget(self.minimize_button)
        self.close_button = QPushButton()
        self.close_button.setIcon(self.style().standardIcon(QStyle.SP_TitleBarCloseButton))
        self.close_button.setStyleSheet(button_style)
        self.close_button.setToolTip("閉じる")
        self.close_button.clicked.connect(self.parent_window.close)
        layout.addWidget(self.close_button)

    def mousePressEvent(self, event):
        # このイベントは MainWindow に移譲して処理させる
        if event.button() == Qt.LeftButton:
            self.parent_window.start_drag_position = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        # マウスの左ボタンが押されている場合のみ、親ウィンドウの移動メソッドを呼び出す
        if event.buttons() == Qt.LeftButton:
            self.parent_window.move_window(event)

class BackgroundWidget(QFrame): # (背景色などを動的に変更するため修正)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.update_style_from_config()

    def update_style_from_config(self):
        self.background_color = config.get_background_color()
        self.border_color = config.get_border_color()
        self.border_radius = float(config.get_border_radius())
        self.update() # 再描画をトリガー

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(self.background_color))
        painter.setPen(QPen(self.border_color, 1))
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.drawRoundedRect(rect, self.border_radius, self.border_radius)

class ScheduleContentWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 15, 30, 20)
        
        self.day_label = QLabel("日付を読み込み中...")
        self.schedule_label = QLabel("")
        self.schedule_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.schedule_label.setWordWrap(True)
        
        layout.addWidget(self.day_label)
        layout.addWidget(self.schedule_label)
        self.schedule_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.day_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.schedule_label.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.update_style_from_config()

    def update_style_from_config(self):
        # フォントと色をまとめて設定
        day_font = config.get_day_font()
        day_color = config.get_day_font_color()
        self.day_label.setFont(day_font)
        self.day_label.setStyleSheet(f"color: {day_color.name()};")
        
        schedule_font = config.get_schedule_font()
        schedule_color = config.get_schedule_font_color()
        self.schedule_label.setFont(schedule_font)
        self.schedule_label.setStyleSheet(f"color: {schedule_color.name()}; line-height: 150%;")
        
        self.update()

    def set_data(self, day_text, schedule_text):
        self.day_label.setText(day_text)
        self.schedule_label.setText(schedule_text)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Desktop Calendar Widget")
        self.start_drag_position = None
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        container = QWidget()
        self.setCentralWidget(container)
        self.background = BackgroundWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.background)

        self.calendar_container = QWidget(self.background)
        self.calendar_container.setContentsMargins(0,0,0,0)

        self.widget1 = ScheduleContentWidget(self.calendar_container)
        self.widget2 = ScheduleContentWidget(self.calendar_container)
        self.current_widget = self.widget1
        self.next_widget = self.widget2
        self.next_widget.hide()

        # タイトルバーの親は MainWindow 自身にする
        self.title_bar = TitleBar(self)
        self.title_bar.settings_requested.connect(self.open_settings_window)
        self.title_bar.hide()
        
        self.title_bar.raise_()

        self.events_by_day = {}
        self.display_days = []
        self.current_day_index = 0
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._trigger_next_display)
        self.gcal_service = None
        
        self.apply_settings()
        self.connect_to_google()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.calendar_container.setGeometry(self.background.rect())
        
        # self.background.width() の代わりに self.width() を使用
        self.title_bar.setGeometry(0, 0, self.width(), self.title_bar.height())
        
        self.widget1.setGeometry(0, 0, self.calendar_container.width(), self.calendar_container.height())
        self.widget2.setGeometry(0, 0, self.calendar_container.width(), self.calendar_container.height())

    def apply_settings(self):
        """設定を読み込み、アプリケーションの全コンポーネントに適用する"""
        self.resize(config.get_window_size())
        self.background.update_style_from_config()
        self.widget1.update_style_from_config()
        self.widget2.update_style_from_config()
        
        interval_ms = config.get_animation_interval() * 1000
        if self.animation_timer.isActive():
            self.animation_timer.start(interval_ms)
        
        self.update()

    def open_settings_window(self):
        if not hasattr(self, 'settings_win') or not self.settings_win.isVisible():
            self.settings_win = SettingsWindow(self.gcal_service, self)
            self.settings_win.settings_changed.connect(self.on_settings_changed)
            self.settings_win.show()

    def on_settings_changed(self):
        """設定変更のシグナルを受け取った時の処理"""
        self.apply_settings()
        self.connect_to_google()

    def connect_to_google(self):
        if not self.gcal_service:
            self.gcal_service = google_auth.get_calendar_service()
        
        if self.gcal_service:
            days = config.get_fetch_days()
            cal_id = config.get_calendar_id()
            if not cal_id:
                cal_id = "primary"
            events = google_auth.get_events(self.gcal_service, calendar_id=cal_id, days_ahead=days)
            self._process_and_display_events(events)
        else:
            self.current_widget.set_data("エラー", "Googleアカウントに接続できませんでした。")
    
    def _process_and_display_events(self, events):
        self.animation_timer.stop()
        self.events_by_day.clear()
        self.display_days.clear()
        self.current_day_index = 0
        
        if not events:
            self.current_widget.set_data("カレンダー", "選択された期間に予定はありません。")
            return
        
        JST = datetime.timezone(datetime.timedelta(hours=9))
        for event in events:
            start_str = event['start'].get('dateTime', event['start'].get('date'))
            dt_local = None
            if 'T' in start_str: dt_local = datetime.datetime.fromisoformat(start_str).astimezone(JST)
            else: dt_local = datetime.datetime.strptime(start_str, '%Y-%m-%d')
            day_key = dt_local.strftime("%Y年%m月%d日 (%a)")
            if day_key not in self.events_by_day: self.events_by_day[day_key] = []
            time_str = dt_local.strftime("%H:%M") if 'T' in start_str else "終日"
            self.events_by_day[day_key].append(f"<b>{time_str}</b> - {event['summary']}")
        
        self.display_days = sorted(self.events_by_day.keys())
        self._update_widget_content(self.current_widget, 0)
        self.current_widget.show()
        self.next_widget.hide()

        if len(self.display_days) > 1:
            self.animation_timer.start(config.get_animation_interval() * 1000)

    def _update_widget_content(self, widget, day_index):
        if not self.display_days: return
        day_key = self.display_days[day_index]
        schedules = "<br>".join(self.events_by_day[day_key])
        widget.set_data(day_key, schedules)
        
    def _trigger_next_display(self):
        if len(self.display_days) <= 1: return
        self.current_day_index = (self.current_day_index + 1) % len(self.display_days)
        self._update_widget_content(self.next_widget, self.current_day_index)
        self._start_animation()
        
    def _start_animation(self):
        container_height = self.calendar_container.height()
        self.current_widget.show()
        self.next_widget.setGeometry(0, container_height, self.calendar_container.width(), container_height)
        self.next_widget.show()
        anim_current = QPropertyAnimation(self.current_widget, b"pos")
        anim_current.setEndValue(QPoint(0, -container_height))
        anim_current.setEasingCurve(QEasingCurve.InOutCubic)
        anim_current.setDuration(700)
        anim_next = QPropertyAnimation(self.next_widget, b"pos")
        anim_next.setEndValue(QPoint(0, 0))
        anim_next.setEasingCurve(QEasingCurve.InOutCubic)
        anim_next.setDuration(700)
        self.anim_group = QParallelAnimationGroup()
        self.anim_group.addAnimation(anim_current)
        self.anim_group.addAnimation(anim_next)
        self.anim_group.finished.connect(self._animation_finished)
        self.anim_group.start()
        
    def _animation_finished(self):
        self.current_widget.hide()
        self.current_widget, self.next_widget = self.next_widget, self.current_widget
        self.anim_group = None
        
    def move_window(self, event):
        if self.start_drag_position:
            self.move(self.pos() + event.globalPosition().toPoint() - self.start_drag_position)
            self.start_drag_position = event.globalPosition().toPoint()
            
    def enterEvent(self, event): self.title_bar.show()
    def leaveEvent(self, event): self.title_bar.hide()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: self.start_drag_position = event.globalPosition().toPoint()
        
    def mouseMoveEvent(self, event): self.move_window(event)
    
    def mouseReleaseEvent(self, event): self.start_drag_position = None

if __name__ == "__main__":
    app = QApplication(sys.argv)

    app_style = """
        QToolTip {
            background-color: #383838; /* 背景色 (ダークグレー) */
            color: #ffffff;            /* 文字色 (白) */
            border: 1px solid #505050;  /* 縁取りの色 */
            padding: 5px;              /* 内側の余白 */
            border-radius: 4px;        /* 角の丸み */
        }
    """
    app.setStyleSheet(app_style)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())