# 領収書処理サーバー for zztkm

zztkm のための領収書処理サーバーです。

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
uvx ryousyusyo --help
```

MCP サーバー
```bash
uvx ryousyusyo-server
```
