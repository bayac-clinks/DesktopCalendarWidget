import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QPushButton, QStyle, QFrame
)
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QIcon
from PySide6.QtCore import Qt, QRectF, QSize, Signal
import google_auth

# --- 定数 ---
# これらは後で設定ファイルから読み込むように変更します
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 220
BACKGROUND_COLOR = QColor(30, 30, 30, 180)  # 少しダークな背景色 (R, G, B, Alpha)
BORDER_COLOR = QColor(80, 80, 80, 220)
BORDER_RADIUS = 15.0

# --- カスタムタイトルバー ---
class TitleBar(QFrame):
    # 親ウィジェットに通知するためのカスタムシグナル
    settings_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setFixedHeight(35)
        self.setStyleSheet("background-color: transparent;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.addStretch() # ボタンを右寄せにするためのスペーサー

        # ボタンのスタイルシート
        button_style = """
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 30);
                border-radius: 4px;
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 20);
            }
        """

        # 設定ボタン
        self.settings_button = QPushButton()
        settings_icon = self.style().standardIcon(QStyle.SP_FileDialogDetailedView)
        self.settings_button.setIcon(settings_icon)
        self.settings_button.setIconSize(QSize(20, 20))
        self.settings_button.setStyleSheet(button_style)
        self.settings_button.setToolTip("設定")
        self.settings_button.clicked.connect(self.settings_requested.emit)
        layout.addWidget(self.settings_button)
        
        # 最小化ボタン
        self.minimize_button = QPushButton()
        minimize_icon = self.style().standardIcon(QStyle.SP_TitleBarMinButton)
        self.minimize_button.setIcon(minimize_icon)
        self.minimize_button.setIconSize(QSize(20, 20))
        self.minimize_button.setStyleSheet(button_style)
        self.minimize_button.setToolTip("最小化")
        self.minimize_button.clicked.connect(self.parent_window.showMinimized)
        layout.addWidget(self.minimize_button)

        # 閉じるボタン
        self.close_button = QPushButton()
        close_icon = self.style().standardIcon(QStyle.SP_TitleBarCloseButton)
        self.close_button.setIcon(close_icon)
        self.close_button.setIconSize(QSize(20, 20))
        self.close_button.setStyleSheet(button_style)
        self.close_button.setToolTip("閉じる")
        self.close_button.clicked.connect(self.parent_window.close)
        layout.addWidget(self.close_button)

    # タイトルバーのドラッグでウィンドウを移動させる
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.parent_window.start_drag_position = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.parent_window.move_window(event)


# --- 背景描画用ウィジェット ---
class BackgroundWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 背景を透明にするための設定
        self.setAttribute(Qt.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing) # アンチエイリアスで滑らかに

        # 背景色と縁取りを設定して角丸の長方形を描画
        painter.setBrush(QBrush(BACKGROUND_COLOR))
        painter.setPen(QPen(BORDER_COLOR, 1))
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.drawRoundedRect(rect, BORDER_RADIUS, BORDER_RADIUS)


# --- メインウィンドウ ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Desktop Calendar Widget")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.start_drag_position = None

        # ウィンドウの標準フレームを非表示にし、背景を透明にする
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 全体のコンテナとなるウィジェット
        container = QWidget()
        self.setCentralWidget(container)
        
        # 背景描画ウィジェットを一番下に配置
        self.background = BackgroundWidget()
        
        # メインレイアウト（垂直方向）
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.background)

        # コンテンツを配置するためのレイアウト（背景ウィジェットの上に重ねる）
        content_layout = QVBoxLayout(self.background)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # カスタムタイトルバー
        self.title_bar = TitleBar(self)
        self.title_bar.settings_requested.connect(self.open_settings_window)
        self.title_bar.hide() # 最初は非表示

        # ここにカレンダー表示ウィジェットなどを追加していく
        # (今は空のウィジェットを配置)
        self.calendar_content = QWidget()

        content_layout.addWidget(self.title_bar)
        content_layout.addWidget(self.calendar_content, 1) # 残りのスペースを全て使う
        # --- Google Calendar 連携 ---
        self.gcal_service = None
        self.connect_to_google()

    def connect_to_google(self):
        """Google APIに接続し、データを取得する"""
        print("Googleアカウントに接続を試みています...")
        self.gcal_service = google_auth.get_calendar_service()

        if self.gcal_service:
            print("\n--- 利用可能なカレンダー一覧 ---")
            calendars = google_auth.get_calendar_list(self.gcal_service)
            if calendars:
                for calendar in calendars:
                    summary = calendar.get('summary')
                    cal_id = calendar.get('id')
                    print(f"- {summary} (ID: {cal_id})")

            print("\n--- 直近一週間の予定 (メインカレンダー) ---")
            events = google_auth.get_events(self.gcal_service)
            if not events:
                print("予定は見つかりませんでした。")
            else:
                for event in events:
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    print(f"{start} - {event['summary']}")
        else:
            print("Googleへの接続に失敗しました。アプリケーションを再起動して試してください。")

    def open_settings_window(self):
        # Phase 6で実装します
        print("設定ウィンドウを開きます。")

    def move_window(self, event):
        if self.start_drag_position:
            self.move(self.pos() + event.globalPosition().toPoint() - self.start_drag_position)
            self.start_drag_position = event.globalPosition().toPoint()

    # --- ウィンドウ全体のイベントハンドラ ---
    def enterEvent(self, event):
        # マウスカーソルがウィンドウ内に入ったらタイトルバーを表示
        self.title_bar.show()

    def leaveEvent(self, event):
        # マウスカーソルがウィンドウ外に出たらタイトルバーを非表示
        self.title_bar.hide()

    def mousePressEvent(self, event):
        # タイトルバー以外の場所をクリックしてもウィンドウを移動できるようにする
        if event.button() == Qt.LeftButton:
            self.start_drag_position = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        self.move_window(event)
    
    def mouseReleaseEvent(self, event):
        self.start_drag_position = None


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())