# ECG Analysis Pipeline

心電図（ECG）データをセッション単位で解析するパイプラインです。
主に次を自動化します。

- セグメントCSVの読み込み（必要に応じて単位変換）
- 信号診断（極性判定、PSD確認、バンドパス）
- Rピーク検出（ピーク情報をJSON出力）
- HRV指標算出（時間領域・周波数領域、CSV集計）
- 診断結果のHTMLレポート生成（Plotly）

## 必要環境

- Python 3.8+（動作確認は 3.10+ 推奨）
- 依存ライブラリ: [requirements.txt](requirements.txt)

## セットアップ

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## ディレクトリ構成（重要）

このプロジェクトの「解析入力」は、セッションごとに分割済みのセグメントCSVです。

```
Data/
	Raw/                       # 元データ（例: Cognionicsの .txt）
	Processed/
		{session}/
			split_segments/        # 解析対象（Step 1が読む）
				01_*.csv
				02_*.csv
	Trigger/                   # トリガー/アノテーション関連（任意）

Results/
	{session}/                 # Step 1/2 の出力先
```

## 入力データ（セグメントCSV）の形式

- 必須: ECG列（列名に `ExGa` を含むものを自動検出）
	- 例: `ExGa 1(uV)`
- 推奨: `Time (s)`（ない場合はサンプリングレートから生成）
- 推奨: `Timestamp`（前処理・分割時の参照用。Step 1/2 では必須ではありません）

単位変換について:

- ECG列名に `uV` が含まれる場合、Step 1 で µV→mV（`/1000`）へ自動変換します。

サンプリングレート:

- デフォルト 500 Hz（[src/analysis_pipeline/config.py](src/analysis_pipeline/config.py)）

## 実行手順（現行パイプライン）

### Step 1: 信号診断 + Rピーク検出（HTML + JSON）

セッション内の全セグメントを処理:

```bash
python src/run_signal_diagnosis.py --session 251216_TK
```

特定セグメントのみ処理（セグメント名 = CSVファイル名（拡張子なし））:

```bash
python src/run_signal_diagnosis.py --session 251216_TK --segment 03_Resting_HR_1_Set1
```

利用可能セッションの一覧（`Data/Processed/{session}/split_segments/*.csv` が存在するもの）:

```bash
python src/run_signal_diagnosis.py --list-sessions
```

### Step 2: HRV指標算出（CSV）

Step 1 で生成された `peaks_*.json` を入力として、HRVを集計します。

```bash
python src/run_hrv_metrics.py --session 251216_TK
```

特定セグメントのみ:

```bash
python src/run_hrv_metrics.py --session 251216_TK --segment 03_Resting_HR_1_Set1
```

## 出力

出力はセッション単位で `Results/{session}/` に保存されます。

- `Results/{session}/diagnosis_{segment}.html`
	- セグメントごとの診断レポート（極性、フィルタ前後波形、PSD、検出ピークなど）
- `Results/{session}/peaks_{segment}.json`
	- 検出ピーク（インデックス・時刻）とメタ情報（反転、skewness、品質ノート等）
- `Results/{session}/hrv_summary.csv`
	- セッション内セグメントのHRV集計（SDNN, RMSSD, pNN50, LF/HF 等）

## 前処理ユーティリティ（必要な場合のみ）

データの整形・アノテーションからの分割などは、`src/` 直下のスクリプト群で行います。
研究データの状況に応じて使い分けてください。

- [src/extract_ecg_columns.py](src/extract_ecg_columns.py)
	- Cognionicsのテキストから解析に必要な列を抽出してCSV化
- [src/detect_trigger_changes.py](src/detect_trigger_changes.py)
	- `TRIGGER(DIGITAL)` の変化点を検出してTimestamp一覧を出力
- [src/insert_virtual_triggers.py](src/insert_virtual_triggers.py)
	- 別セッション等のトリガー列を基準点からオフセットコピーして補完
- [src/deduplicate_triggers.py](src/deduplicate_triggers.py)
	- 連続重複トリガー削除
- [src/add_annotation.py](src/add_annotation.py)
	- 既存CSVに `Annotation` 列を追記
- [src/split_by_annotation.py](src/split_by_annotation.py)
	- アノテーションペアに基づき `split_segments/` を生成

## プロジェクト構成（現状）

```
ECG_Analize/
	src/
		analysis_pipeline/
			config.py
			io_utils.py
			preprocess.py
			diagnosis.py
			rpeak.py
			hrv.py
		run_signal_diagnosis.py
		run_hrv_metrics.py
		extract_ecg_columns.py
		split_by_annotation.py
		detect_trigger_changes.py
		insert_virtual_triggers.py
		deduplicate_triggers.py
		add_annotation.py
		visualize_ecg.py
	Data/
	Results/
	References/
	requirements.txt
	README.md
```

## 参考

- [References/Analysis.R](References/Analysis.R) にR実装の処理が残っています（ピーク検出の整合などの参照用）。
