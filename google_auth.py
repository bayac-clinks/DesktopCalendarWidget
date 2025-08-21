import os
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- 定数 ---
# このスコープはカレンダーの読み取り権限を要求します。
# もし将来的に書き込みもしたくなったら、URLの readonly を外します。
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'

def get_calendar_service():
    """
    Google Calendar APIサービスを認証して取得する。
    token.jsonが存在すればそれを使用し、なければブラウザで認証フローを開始する。
    """
    creds = None
    # token.json があれば、認証情報を読み込む
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    # 認証情報がないか、無効な場合
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"トークンのリフレッシュに失敗: {e}")
                # リフレッシュ失敗時はファイルを削除して再認証
                os.remove(TOKEN_FILE)
                creds = None
        
        # 認証情報がまだない場合は、ブラウザで認証フローを開始
        if not creds:
            if not os.path.exists(CREDENTIALS_FILE):
                print(f"エラー: 認証情報ファイル '{CREDENTIALS_FILE}' が見つかりません。")
                return None
            
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            # run_local_server は自動でブラウザを開き、認証後にサーバーを閉じる
            creds = flow.run_local_server(port=0)
        
        # 新しい認証情報を token.json に保存
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('calendar', 'v3', credentials=creds)
        print("Google Calendar APIへの接続に成功しました。")
        return service
    except HttpError as error:
        print(f"APIサービスのビルド中にエラーが発生しました: {error}")
        return None

def get_calendar_list(service):
    """利用可能なカレンダーの一覧を取得する"""
    if not service:
        return []
    try:
        calendar_list = service.calendarList().list().execute()
        return calendar_list.get('items', [])
    except HttpError as error:
        print(f"カレンダーリストの取得中にエラーが発生しました: {error}")
        return []

def get_events(service, calendar_id='primary', days_ahead=7):
    """
    指定されたカレンダーから、今後指定された日数分のイベントを取得する。
    calendar_id='primary'はメインカレンダーを意味する。
    """
    if not service:
        return []
    
    # イベント取得期間を設定
    now_utc = datetime.datetime.utcnow()
    time_min = now_utc.isoformat() + 'Z'  # 'Z' indicates UTC time
    time_max = (now_utc + datetime.timedelta(days=days_ahead)).isoformat() + 'Z'

    try:
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=50,  # 取得する最大件数
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        return events
    except HttpError as error:
        print(f"イベントの取得中にエラーが発生しました: {error}")
        return []