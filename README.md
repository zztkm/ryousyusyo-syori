# 領収書処理サーバー for zztkm

zztkm のための領収書処理ツールです。

## Requirements

- [Ollama](https://ollama.com/)

### Ollama で利用するモデル

現在このツールが利用するモデルはデフォルトで以下のようになってます。

- CLI
  - `gemma3:12b`
  - CLI 引数 `--model` で変更可能
- MCP サーバー
  - `gemma3:12b`
  - 指定不可

そのため、`ollama pull gemma3:12b` を実行してモデルをダウンロードしておく必要があります。

## Install

```bash
uv tool install git+https://github.com/zztkm/ryousyusyo-syori
```

2 つのツールがインストールされます。

- `ryousyusyo`: 領収書の画像を処理する CLI ツール
- `ryousyusyo-server`: 領収書画像処理を行う MCP サーバー

## Usage

CLI ツール
```bash
uvx --from ryousyusyo-syori ryousyusyo --help
```

MCP サーバーを起動するには以下のコマンドを実行します (stdio モードで実行されます)。
```bash
uvx --from ryousyusyo-syori ryousyusyo-server
```

### Usage for Claude Desktop

Claude Desktop で使用する場合は、以下のように MCP サーバーを設定します（Install の章で説明したように、`ryousyusyo-syori` をインストールしていることが前提です）。

`claude_desktop_config.json`

```json
{
  "mcpServers": {
    "receiptProcessor": {
      "command": "uvx",
      "args": [
        "--from",
        "ryousyusyo-syori",
        "ryousyusyo-server"
      ]
    }
  }
}
```

これを設定後、Claude Desktop を再起動します。

そうすると、MCP サーバーを認識した状態になるため、以下のようなプロンプトを入力して領収書情報を抽出できます。

※ 画像パスは絶対パスで指定してください。

```txt
"C:\Users\you\Downloads\test.jpg"
このレシート画像の情報を抽出してください
```

![mcp usage example](mcp-usage.png)

## Reference

- [TypeScript で MCP サーバーを実装し、Claude Desktop から利用する](https://azukiazusa.dev/blog/typescript-mcp-server)
- [Welcome to FastMCP 2.0! - FastMCP](https://gofastmcp.com/getting-started/welcome)
- [ollama/ollama-python: Ollama Python library](https://github.com/ollama/ollama-python)

## License

[MIT License](LICENSE)

## Author

- [zztkm](github.com/zztkm)

## 検証中のツール

MCP を使うことがないなと感じているため、以下の main.py に移行中

### main.py スクリプトで領収書のリネームを行う

`main.py` は入力ディレクトリ内の PDF・画像ファイルを一括処理し、領収書情報（日付・発行元・税込金額）を抽出して `{YYYYMMDD}_{発行元}_{税込金額}.{ext}` の形式でリネームコピーするスクリプトです。

#### 前提条件

抽出用モデルに加えて、画像の OCR 用モデルも必要です。

```bash
ollama pull gemma3:12b
ollama pull glm-ocr
```

gemma3:4b などの軽量モデルだと領収書情報の収集精度が低いため 12b を利用することをおすすめする。
システムプロンプトの調整などで対応するか、前処理を強化すれば 4b モデルでも活用できるかもしれない。

#### 実行方法

```bash
uv run main.py
```

#### CLI 引数

| 引数 | 説明 | デフォルト |
|------|------|------------|
| `--input` | 入力ディレクトリ | `./input` |
| `--model` | 抽出用モデル | `gemma3:12b` |
| `--ocr-model` | OCR 用モデル | `glm-ocr` |
| `--dry-run` | コピーなしで解析結果のみ表示 | - |

#### 対応ファイル形式

- PDF (`.pdf`)
- 画像 (`.jpg`, `.jpeg`, `.png`)

#### 出力先

`./dist` ディレクトリにリネームされたファイルがコピーされます。

