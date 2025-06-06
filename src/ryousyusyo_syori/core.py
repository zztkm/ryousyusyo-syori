from pathlib import Path
from dataclasses import dataclass
from ollama import chat
from ollama import ChatResponse
import json


@dataclass
class ReceiptInfo:
    """領収書から抽出された情報"""

    date: str
    store_name: str
    amount: str

    def to_filename(self) -> str:
        """ファイル名形式に変換"""
        return f"{self.date}_{self.store_name}_{self.amount}"


def extract_receipt_info(image_path: Path, model: str) -> ReceiptInfo:
    content = """
    この画像は領収書です。この画像から日付、店名、領収金額を抽出してください。
    - 日付は YYYYMMDD 形式
    - 店名が判別できない場合は `不明` とする
    - 領収金額は数字のみを含む文字列

    返却値の形式は JSON で、以下のキーを含めてください:
    - date: 領収書の日付
    - store_name: 店名
    - amount: 領収金額
"""
    messages = [
        {
            "role": "user",
            "content": content,
            "images": [str(image_path.absolute())],
        }
    ]
    # keep_aliveを0に設定して、応答が完了したら接続を閉じる
    # そうすることで、次のリクエストに影響を与えないようにする
    res: ChatResponse = chat(
        model=model, messages=messages, format="json", keep_alive=0
    )
    data = json.loads(res.message.content)
    return ReceiptInfo(
        date=data.get("date", ""),
        store_name=data.get("store_name", ""),
        amount=data.get("amount", ""),
    )
