"""領収書PDF/画像を一括処理し、情報を抽出してリネームコピーするCLIツール"""

import argparse
import logging
import json
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import ollama
import pdfplumber

logging.getLogger("pdfminer").setLevel(logging.ERROR)

PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
SUPPORTED_EXTENSIONS = PDF_EXTENSIONS | IMAGE_EXTENSIONS
FORBIDDEN_CHARS = re.compile(r'[<>:"/\\|?*]')
MAX_FILENAME_LENGTH = 60


def ocr_image(image_path: Path, model: str) -> str:
    """glm-ocr等のOCRモデルで画像からテキストを認識する"""
    res = ollama.chat(
        model=model,
        messages=[
            {
                "role": "user",
                "content": "Text Recognition:",
                "images": [str(image_path.absolute())],
            }
        ],
        keep_alive=0,
    )
    return res.message.content


def extract_text_from_pdf(pdf_path: Path) -> str:
    """pdfplumberで全ページのテキストを抽出する"""
    texts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                texts.append(text)
    return "\n".join(texts)


def extract_receipt_info(text: str, model: str) -> dict:
    """テキストから領収書情報(日付・発行元・税込金額)をStructured Outputsで抽出する"""
    schema = {
        "type": "object",
        "properties": {
            "payment_date": {
                "type": "string",
                "description": "支払日をYYYYMMDD形式で。不明なら空文字",
            },
            "issuer": {
                "type": "string",
                "description": "発行元(店名・企業名)。不明なら空文字",
            },
            "amount_tax_included_jpy": {
                "type": "integer",
                "description": "税込金額(円)。不明なら0",
            },
        },
        "required": ["payment_date", "issuer", "amount_tax_included_jpy"],
    }

    content = """以下のテキストは領収書の内容です。以下の情報を抽出してください:
- payment_date: 支払日(YYYYMMDD形式)
- issuer: 発行元(店名・企業名)
- amount_tax_included_jpy: 税込金額(円、整数)

テキスト:
"""
    res = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": content + text}],
        format=schema,
        keep_alive=0,
        options={"num_predict": 1024},
        think=False,
    )
    return json.loads(res.message.content)


def validate_date(date_str: str) -> str | None:
    """YYYYMMDD形式の日付文字列を検証する。不正ならNoneを返す"""
    if not date_str or not re.fullmatch(r"\d{8}", date_str):
        return None
    try:
        datetime.strptime(date_str, "%Y%m%d")
        return date_str
    except ValueError:
        return None


def sanitize_filename(name: str) -> str:
    """ファイル名に使えない文字を_に置換し、60文字以内に切り詰める"""
    sanitized = FORBIDDEN_CHARS.sub("_", name)
    return sanitized[:MAX_FILENAME_LENGTH]


def generate_output_path(dist_dir: Path, date: str | None, issuer: str | None, amount: int | None, ext: str) -> Path:
    """出力ファイルパスを生成する。同名衝突時は連番を付与"""
    date_part = date if date else "不明日付"
    issuer_part = sanitize_filename(issuer) if issuer else "不明発行元"
    amount_part = str(amount) if amount and amount > 0 else "不明金額"

    base_name = f"{date_part}_{issuer_part}_{amount_part}"
    candidate = dist_dir / f"{base_name}{ext}"

    if not candidate.exists():
        return candidate

    counter = 2
    while True:
        candidate = dist_dir / f"{base_name}_{counter}{ext}"
        if not candidate.exists():
            return candidate
        counter += 1


def process_file(
    file_path: Path,
    model: str,
    ocr_model: str,
    dist_dir: Path,
    dry_run: bool,
) -> dict:
    """1ファイルを処理し、結果辞書を返す"""
    start = time.time()
    result = {
        "input_path": str(file_path),
        "output_path": None,
        "status": "OK",
        "error": None,
        "model": None,
        "elapsed": 0.0,
    }
    ext = file_path.suffix.lower()

    def _log(msg: str):
        elapsed = time.time() - start
        print(f"  [{elapsed:6.1f}s] {msg}", flush=True)

    # テキスト抽出
    try:
        if ext in PDF_EXTENSIONS:
            result["model"] = model
            _log(f"PDF テキスト抽出開始 (pdfplumber)")
            text = extract_text_from_pdf(file_path)
            _log(f"PDF テキスト抽出完了 ({len(text)}文字)")
            if not text.strip():
                result["status"] = "WARN"
                result["error"] = "PDFからテキストを抽出できませんでした"
        elif ext in IMAGE_EXTENSIONS:
            result["model"] = f"{ocr_model} + {model}"
            _log(f"OCR 開始 (model: {ocr_model})")
            text = ocr_image(file_path, ocr_model)
            _log(f"OCR 完了 ({len(text)}文字)")
        else:
            result["status"] = "FAIL"
            result["error"] = f"未対応の拡張子: {ext}"
            return result
    except Exception as e:
        result["status"] = "FAIL"
        result["error"] = f"テキスト抽出エラー: {e}"
        text = ""

    # 領収書情報抽出
    info = {}
    if text.strip():
        try:
            _log(f"情報抽出開始 (model: {model})")
            info = extract_receipt_info(text, model)
            _log(f"情報抽出完了: {info}")
        except Exception as e:
            if result["status"] == "OK":
                result["status"] = "WARN"
            result["error"] = f"情報抽出エラー: {e}"

    date = validate_date(info.get("payment_date", ""))
    issuer = info.get("issuer", "") or None
    amount = info.get("amount_tax_included_jpy", 0) or None

    if not date or not issuer or not amount:
        if result["status"] == "OK":
            result["status"] = "WARN"
        if not result["error"]:
            result["error"] = "一部の情報を抽出できませんでした"

    output_path = generate_output_path(dist_dir, date, issuer, amount, ext)
    result["output_path"] = str(output_path)

    if not dry_run:
        try:
            dist_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, output_path)
        except Exception as e:
            result["status"] = "FAIL"
            result["error"] = f"コピーエラー: {e}"

    result["elapsed"] = time.time() - start
    return result


def main():
    parser = argparse.ArgumentParser(
        description="領収書PDF/画像を一括処理し、情報を抽出してリネームコピーする。"
        " 事前に ollama で領収書情報抽出用モデル(デフォルト: gemma3:12b)と"
        " 画像の OCR 用モデル(デフォルト: glm-ocr)を pull しておく必要があります。"
    )
    parser.add_argument(
        "--input", default="./input", help="入力ディレクトリ (デフォルト: ./input)"
    )
    parser.add_argument(
        "--model", default="gemma3:12b", help="抽出用モデル (デフォルト: gemma3:12b)"
    )
    parser.add_argument(
        "--ocr-model", default="glm-ocr", help="OCR用モデル (デフォルト: glm-ocr)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="コピーなしで解析結果のみ表示"
    )
    args = parser.parse_args()

    input_dir = Path(args.input)
    if not input_dir.is_dir():
        print(f"エラー: 入力ディレクトリが見つかりません: {input_dir}", file=sys.stderr)
        sys.exit(1)

    dist_dir = Path("./dist")

    # 対象ファイル列挙
    files = sorted(
        f for f in input_dir.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    if not files:
        print(f"対象ファイルが見つかりません: {input_dir}")
        sys.exit(0)

    print(f"対象ファイル数: {len(files)}")
    print(f"抽出モデル: {args.model} / OCRモデル: {args.ocr_model}")
    if args.dry_run:
        print("[DRY RUN] コピーは行いません")
    print()

    results = []
    for file_path in files:
        print(f"処理中: {file_path.name} ...", flush=True)
        result = process_file(file_path, args.model, args.ocr_model, dist_dir, args.dry_run)
        results.append(result)

        status = result["status"]
        output_name = Path(result["output_path"]).name if result["output_path"] else "N/A"
        elapsed = f"{result['elapsed']:.1f}s"
        model_info = result["model"] or "-"
        if status == "OK":
            print(f"  [OK]   {file_path.name} -> {output_name}  (model: {model_info}, {elapsed})")
        elif status == "WARN":
            print(f"  [WARN] {file_path.name} -> {output_name}  (model: {model_info}, {elapsed}) ({result['error']})")
        else:
            print(f"  [FAIL] {file_path.name}  (model: {model_info}, {elapsed}) ({result['error']})")
        print()

    # 集計
    ok_count = sum(1 for r in results if r["status"] == "OK")
    warn_count = sum(1 for r in results if r["status"] == "WARN")
    fail_count = sum(1 for r in results if r["status"] == "FAIL")
    total_elapsed = sum(r["elapsed"] for r in results)
    print("--- 結果 ---")
    print(f"OK: {ok_count}  WARN: {warn_count}  FAIL: {fail_count}  合計: {len(results)}")
    print(f"合計処理時間: {total_elapsed:.1f}s")


if __name__ == "__main__":
    main()
