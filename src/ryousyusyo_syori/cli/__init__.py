from pathlib import Path
from argparse import ArgumentParser
import shutil

from ryousyusyo_syori.core import extract_receipt_info


def run():
    parser = ArgumentParser(
        description="領収書画像から情報を抽出してファイル名を変更します"
    )
    parser.add_argument("image_path", help="領収書画像のパス")
    parser.add_argument("--model", default="gemma3:12b", help="使用するモデル")
    args = parser.parse_args()

    image_path = Path(args.image_path)
    receipt_info = extract_receipt_info(image_path, args.model)

    new_image_path = (
        image_path.parent / f"{receipt_info.to_filename()}{image_path.suffix}"
    )
    shutil.copy(
        image_path,
        new_image_path,
    )
    print(f"新しい画像のパス: {new_image_path}")
