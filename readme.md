# AIアバター動画無音削除・倍速ツール

AIアバター動画から無音部分を自動検出・削除し、倍速処理を行うPythonツールです。

## 特徴

- **2つの処理方法**: 基本検出またはAI音声分離（Spleeter）
- **自然な間隔保持**: セリフ間にマージンを設けて自然な会話の流れを維持
- **カスタマイズ可能**: 閾値、最小時間、マージン、倍速設定を調整可能
- **詳細レポート**: 処理結果を詳細にレポート出力
- **簡単操作**: コマンドライン引数で動画ファイルを指定するだけ

## 環境要件

- Python 3.9
- conda または venv

## インストール

### conda環境（推奨）

```bash
# conda環境を作成
conda create -n ai_avatar_tool python=3.9
conda activate ai_avatar_tool

# 必要ライブラリをインストール
pip install numpy==1.21.1 scipy==1.7.3 librosa==0.8.1 soundfile==0.12.1 moviepy==1.0.3 pydub==0.25.1 tensorflow==2.8.4 spleeter==2.3.2 pyinstaller==5.13.2 matplotlib==3.5.3
```

### システム要件

- FFmpeg（動画処理に必要）

```bash
# Ubuntu/WSL
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
# https://ffmpeg.org/download.html からダウンロード
```

## 使用方法

### 基本的な使い方

コマンドライン引数で処理したい動画ファイルを指定してツールを実行：

```bash
python video_cutter.py <動画ファイル名>
```

**例:**
```bash
python video_cutter.py my_video.mp4
python video_cutter.py "C:\Videos\test.mp4"
python video_cutter.py /home/user/videos/sample.mp4
```

### 出力ファイル名の自動生成

入力ファイル名に `_processed` が自動追加されます：
- `my_video.mp4` → `my_video_processed.mp4`
- `test.avi` → `test_processed.avi`
- `sample.mov` → `sample_processed.mov`

### 処理方法の選択

**方法1: 基本検出（推奨）**
- 元音声（セリフ+BGM）で無音検出
- 高速処理
- ほとんどのAIアバター動画で十分な精度

**方法2: AI音声分離（Spleeter）**
- セリフとBGMを分離してから無音検出
- より高精度だが処理時間が長い
- BGMが大きい場合に有効

## 設定オプション

スクリプト内の `SETTINGS` 辞書を編集して設定を変更できます：

| 設定項目 | デフォルト値 | 説明 |
|---------|-------------|------|
| processing_mode | "basic" | `"basic"`: 基本検出, `"spleeter"`: AI音声分離 |
| min_silence_duration | 1.0秒 | この時間未満の無音は無視 |
| margin | 0.5秒 | 無音部分の前後に残す時間（セリフ間の自然な間を確保） |
| threshold | "auto" | `"auto"`: 自動設定, または `-30`, `-35`, `-40` など手動指定 |
| speed_factor | 1.15倍 | 出力動画の再生速度 |

## 出力ファイル

- `<入力ファイル名>_processed.<拡張子>`: 処理済み動画
- `processing_report.txt`: 詳細処理レポート

## 設定例

### 設定例1: 高速処理（デフォルト）
```python
SETTINGS = {
    "processing_mode": "basic",
    "min_silence_duration": 1.0,
    "margin": 0.5,
    "threshold": "auto",
    "speed_factor": 1.15
}
```

### 設定例2: 高精度処理
```python
SETTINGS = {
    "processing_mode": "spleeter",
    "min_silence_duration": 0.8,  # より細かく検出
    "margin": 0.3,  # より短いマージン
    "threshold": "auto",
    "speed_factor": 1.2
}
```

### 設定例3: 保守的処理
```python
SETTINGS = {
    "processing_mode": "basic",
    "min_silence_duration": 2.0,  # より長い無音のみ削除
    "margin": 0.8,  # より長いマージン
    "threshold": -30,  # より緩い閾値
    "speed_factor": 1.1
}
```

## 処理の流れ

1. **引数確認**: コマンドライン引数から入力ファイルを取得
2. **音声抽出**: 動画から音声を抽出
3. **無音検出**: 設定に基づいて無音部分を検出
4. **セグメント計算**: マージンを考慮した保持セグメントを計算
5. **動画処理**: FFmpegで無音削除と倍速処理
6. **レポート生成**: 処理結果の詳細レポートを出力

## 自動閾値について

`threshold = "auto"` の場合、動画の音声レベルを分析して最適な閾値を自動設定します：
- 音声レベルが -25dB以上: 閾値 -35dB
- 音声レベルが -30dB以上: 閾値 -40dB  
- 音声レベルが -30dB未満: 閾値 -45dB

## トラブルシューティング

### よくある問題

**1. ファイルが指定されていない**
```bash
# エラー: 入力ファイルが指定されていません。
# 解決: 動画ファイルを引数として指定
python video_cutter.py your_video.mp4
```

**2. ファイルが見つからない**
```bash
# エラー: ファイルが見つかりません
# 解決: ファイルパスを確認、またはフルパスで指定
python video_cutter.py "C:\full\path\to\video.mp4"
```

**3. FFmpegが見つからない**
```bash
# エラー: 'ffmpeg' is not recognized
# 解決: FFmpegをインストールしてPATHに追加
```

**4. ライブラリインストールエラー**
```bash
# Python 3.12では互換性問題あり
# 解決: Python 3.9を使用
```

**5. メモリ不足**
```bash
# 長い動画でメモリ不足の場合
# 解決: 動画を短く分割してから処理
```

## 実行例

```bash
# 現在のディレクトリの動画を処理
python video_cutter.py sample.mp4

# 別フォルダの動画を処理
python video_cutter.py videos/presentation.mp4

# スペースを含むファイル名の場合
python video_cutter.py "My Avatar Video.mp4"

# 処理開始時に設定が表示される
# 出力: sample_processed.mp4
# レポート: processing_report.txt
```

## ライセンス

このツールは以下のオープンソースライブラリを使用しています：
- MoviePy (MIT License)
- PyDub (MIT License) 
- Spleeter (MIT License)
- FFmpeg (LGPL/GPL)

## 更新履歴

- v1.0: 基本的な無音削除機能
- v1.1: AI音声分離（Spleeter）対応
- v1.2: マージン機能追加、設定カスタマイズ対応
- v1.3: コマンドライン引数対応、出力ファイル名自動生成

