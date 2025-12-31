# ECG Analysis Pipeline

心電図（ECG）データの自動解析パイプラインです。R波検出、RR間隔の計算、心拍変動（HRV）指標の算出、および品質管理レポートの生成を行います。

## 機能

- **ECGデータの前処理**: フィルタリング、デトレンド処理
- **R波検出**: 自動ピーク検出アルゴリズム
- **RR間隔計算**: クリーニング処理を含む
- **HRV指標**: 時間領域・周波数領域の心拍変動解析
- **品質管理レポート**: インタラクティブなHTMLレポート生成

## 必要環境

- Python 3.8以上
- 依存ライブラリは[requirements.txt](requirements.txt)を参照

## インストール

```bash
# リポジトリのクローン
git clone https://github.com/YOUR_USERNAME/ECG_Analize.git
cd ECG_Analize

# 仮想環境の作成と有効化
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate  # Windows

# 依存関係のインストール
pip install -r requirements.txt
```

## 使い方

### データの準備

1. 生データを`Data/Raw/`に配置
2. 前処理済みデータを`Data/Processed/`に配置

### データ形式

サンプルデータは[Data/Example/sample_ecg.csv](Data/Example/sample_ecg.csv)を参照してください。

**データ形式**：
- `Time (s)`: 時刻（秒）
- `Timestamp`: タイムスタンプ（日時）
- `ECG (uV)`: 心電図信号（マイクロボルト）
- `Packet Counter(DIGITAL)`: パケットカウンタ
- `TRIGGER(DIGITAL)`: トリガー信号

サンプリングレート: 500 Hz (デフォルト設定)

### パイプラインの実行

```bash
# セグメント分割されたデータの解析
python -m src.pipeline.runner Data/Processed/251216_TK/split_segments --output-dir Results/251216_TK
```

### 出力

結果は指定したディレクトリに出力されます：
- `*_rri.csv`: RR間隔データ
- `hrv_summary.csv`: HRV指標のサマリー
- `figures/*_qc.html`: 品質管理レポート（インタラクティブ）

## プロジェクト構成

```
ECG_Analize/
├── src/
│   ├── pipeline/          # メインパイプライン
│   │   ├── runner.py      # パイプライン実行エントリーポイント
│   │   ├── preprocess.py  # 前処理
│   │   ├── rpeak_detect.py # R波検出
│   │   ├── rr_clean.py    # RR間隔クリーニング
│   │   ├── hrv_metrics.py # HRV指標計算
│   │   └── qc_report.py   # 品質管理レポート
│   ├── extract_ecg_columns.py
│   ├── split_by_annotation.py
│   └── ...
├── Data/                  # データディレクトリ（.gitignoreで除外）
│   ├── Raw/
│   ├── Processed/
│   └── Trigger/
├── Results/               # 結果ディレクトリ（.gitignoreで除外）
├── requirements.txt
└── README.md
```

## 依存ライブラリ

- **pandas**: データ処理
- **numpy**: 数値計算
- **scipy**: 信号処理
- **neurokit2**: 生体信号解析
- **plotly**: インタラクティブ可視化
- **mne**: 生体信号処理

## ライセンス

このプロジェクトは研究目的で開発されています。

## 貢献

バグ報告や機能リクエストは、Issueで受け付けています。

## 開発者

心拍データ解析プロジェクト
