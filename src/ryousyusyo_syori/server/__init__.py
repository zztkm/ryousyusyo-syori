from pathlib import Path
from fastmcp import FastMCP
from ryousyusyo_syori.core import extract_receipt_info

# refs: https://gofastmcp.com/servers/fastmcp#creating-a-server
mcp = FastMCP(
    name="領収書処理サーバー",
    instructions="""
このサーバーはあなたのマシンにインストールされた Ollama を利用して、領収書の画像を処理し、日付、店名、領収金額を抽出するためのツールを提供します。
    """,
)


@mcp.tool()
def process_receipt(image_path: str) -> dict[str, str]:
    """
    領収書の画像を処理し、日付、店名、領収金額を抽出するツール
    """
    receipt_info = extract_receipt_info(Path(image_path), "gemma3:12b")
    return {
        "date": receipt_info.date,
        "store_name": receipt_info.store_name,
        "amount": receipt_info.amount,
    }


def run():
    """
    FastMCP サーバーを起動する関数
    """
    mcp.run()
