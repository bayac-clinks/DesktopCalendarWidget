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

# --- 定数 ---
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 220
BACKGROUND_COLOR = QColor(30, 30, 30, 180)
BORDER_COLOR = QColor(80, 80, 80, 220)
BORDER_RADIUS = 15.0
ANIMATION_INTERVAL = 10000  # 10秒
ANIMATION_DURATION = 700    # 0.7秒

# --- カスタムタイトルバー (変更なし) ---
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
        button_style = """
            QPushButton { background-color: transparent; border: none; padding: 5px; }
            QPushButton:hover { background-color: rgba(255, 255, 255, 30); border-radius: 4px; }
            QPushButton:pressed { background-color: rgba(255, 255, 255, 20); }
        """
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
        if event.button() == Qt.LeftButton: self.parent_window.start_drag_position = event.globalPosition().toPoint()
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton: self.parent_window.move_window(event)

# --- 背景描画用ウィジェット (変更なし) ---
class BackgroundWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(BACKGROUND_COLOR))
        painter.setPen(QPen(BORDER_COLOR, 1))
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.drawRoundedRect(rect, BORDER_RADIUS, BORDER_RADIUS)

# --- スケジュール表示用ウィジェット (新規追加) ---
class ScheduleContentWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 15, 30, 20)
        
        self.day_label = QLabel("日付を読み込み中...")
        font_day = QFont("Yu Gothic UI", 20)
        font_day.setBold(True)
        self.day_label.setFont(font_day)
        self.day_label.setStyleSheet("color: #FFFFFF;")
        
        self.schedule_label = QLabel("")
        font_schedule = QFont("Yu Gothic UI", 12)
        self.schedule_label.setFont(font_schedule)
        self.schedule_label.setStyleSheet("color: #EAEAEA; line-height: 150%;")
        self.schedule_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.schedule_label.setWordWrap(True)
        
        layout.addWidget(self.day_label)
        layout.addWidget(self.schedule_label)
        self.schedule_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_data(self, day_text, schedule_text):
        self.day_label.setText(day_text)
        self.schedule_label.setText(schedule_text)


# --- メインウィンドウ (大幅更新) ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Desktop Calendar Widget")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.start_drag_position = None

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        container = QWidget()
        self.setCentralWidget(container)
        self.background = BackgroundWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.background)
        content_layout = QVBoxLayout(self.background)
        content_layout.setContentsMargins(0, 0, 0, 0)

        self.title_bar = TitleBar(self)
        self.title_bar.settings_requested.connect(self.open_settings_window)
        self.title_bar.hide()

        # --- アニメーションとスケジュール表示のセットアップ ---
        self.calendar_container = QWidget() # はみ出した部分を隠すためのコンテナ
        self.calendar_container.setContentsMargins(0,0,0,0)
        
        # 表示用ウィジェットを2つ用意 (現在用と次用)
        self.widget1 = ScheduleContentWidget(self.calendar_container)
        self.widget2 = ScheduleContentWidget(self.calendar_container)
        self.current_widget = self.widget1
        self.next_widget = self.widget2
        self.next_widget.hide() # 最初は隠す

        content_layout.addWidget(self.title_bar)
        content_layout.addWidget(self.calendar_container, 1)

        # スケジュールデータ関連
        self.events_by_day = {}
        self.display_days = []
        self.current_day_index = 0

        # アニメーションタイマー
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._trigger_next_display)

        # Google Calendar 連携
        self.gcal_service = None
        self.connect_to_google()

    def resizeEvent(self, event):
        """ウィンドウサイズ変更時にウィジェットのサイズも追従させる"""
        super().resizeEvent(event)
        self.widget1.setGeometry(0, 0, self.calendar_container.width(), self.calendar_container.height())
        self.widget2.setGeometry(0, 0, self.calendar_container.width(), self.calendar_container.height())


    def connect_to_google(self):
        """Google APIに接続し、データを取得して表示する"""
        self.gcal_service = google_auth.get_calendar_service()
        if self.gcal_service:
            events = google_auth.get_events(self.gcal_service)
            self._process_and_display_events(events)
        else:
            self.current_widget.set_data("エラー", "Googleアカウントに接続できませんでした。")

    def _process_and_display_events(self, events):
        """イベントデータを日付ごとに整形し、初回表示を行う"""
        if not events:
            self.current_widget.set_data("カレンダー", "直近の予定はありません。")
            return

        self.events_by_day = {}
        JST = datetime.timezone(datetime.timedelta(hours=9))

        for event in events:
            start_str = event['start'].get('dateTime', event['start'].get('date'))
            dt_local = None
            if 'T' in start_str:
                dt_obj = datetime.datetime.fromisoformat(start_str)
                dt_local = dt_obj.astimezone(JST)
            else:
                dt_local = datetime.datetime.strptime(start_str, '%Y-%m-%d')

            day_key = dt_local.strftime("%Y年%m月%d日 (%a)")
            if day_key not in self.events_by_day:
                self.events_by_day[day_key] = []

            time_str = dt_local.strftime("%H:%M") if 'T' in start_str else "終日"
            self.events_by_day[day_key].append(f"<b>{time_str}</b> - {event['summary']}")
        
        self.display_days = sorted(self.events_by_day.keys())
        
        # 初回表示
        self._update_widget_content(self.current_widget, 0)

        # 表示する日が複数あればアニメーションタイマーを開始
        if len(self.display_days) > 1:
            self.animation_timer.start(ANIMATION_INTERVAL)

    def _update_widget_content(self, widget, day_index):
        """指定ウィジェットの内容を更新"""
        if not self.display_days: return
        day_key = self.display_days[day_index]
        schedules = "<br>".join(self.events_by_day[day_key])
        widget.set_data(day_key, schedules)

    def _trigger_next_display(self):
        """アニメーションの準備と開始"""
        if len(self.display_days) <= 1: return

        self.current_day_index = (self.current_day_index + 1) % len(self.display_days)
        self._update_widget_content(self.next_widget, self.current_day_index)
        self._start_animation()

    def _start_animation(self):
        """リールアニメーションを実行"""
        container_height = self.calendar_container.height()
        self.current_widget.show()
        self.next_widget.setGeometry(0, container_height, self.calendar_container.width(), container_height)
        self.next_widget.show()

        anim_current = QPropertyAnimation(self.current_widget, b"pos")
        anim_current.setEndValue(QPoint(0, -container_height))
        anim_current.setEasingCurve(QEasingCurve.InOutCubic)
        anim_current.setDuration(ANIMATION_DURATION)

        anim_next = QPropertyAnimation(self.next_widget, b"pos")
        anim_next.setEndValue(QPoint(0, 0))
        anim_next.setEasingCurve(QEasingCurve.InOutCubic)
        anim_next.setDuration(ANIMATION_DURATION)

        self.anim_group = QParallelAnimationGroup()
        self.anim_group.addAnimation(anim_current)
        self.anim_group.addAnimation(anim_next)
        self.anim_group.finished.connect(self._animation_finished)
        self.anim_group.start()

    def _animation_finished(self):
        """アニメーション完了後の処理"""
        self.current_widget.hide()
        # ウィジェットの役割を交換して次のアニメーションに備える
        self.current_widget, self.next_widget = self.next_widget, self.current_widget
        self.anim_group = None

    def open_settings_window(self):
        print("設定ウィンドウを開きます。")
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
    window = MainWindow()
    window.show()
    sys.exit(app.exec())