#!/usr/bin/env python3
"""
トリガーCSVファイルから連続する重複トリガーを削除し、Trigger_Value列を削除するプログラム

使用方法:
    python3 deduplicate_triggers.py <ディレクトリパス>
"""

import pandas as pd
import argparse
from pathlib import Path


def deduplicate_triggers(input_file: str, output_file: str | None = None) -> None:
    """
    連続する重複トリガーを削除し、Trigger_Value列を削除する
    
    Args:
        input_file: 入力CSVファイルのパス
        output_file: 出力CSVファイルのパス（Noneの場合は入力ファイルを上書き）
    """
    # CSVファイルを読み込む
    df = pd.read_csv(input_file)
    
    print(f"処理前: {len(df)} 行")
    
    # 連続する重複行を削除（Annotationが連続して同じ値の場合に削除）
    # shift()で1行前のAnnotationと比較し、異なる行のみを保持
    df_deduplicated = df[df['Annotation'] != df['Annotation'].shift(1)]
    
    print(f"重複削除後: {len(df_deduplicated)} 行")
    
    # Trigger_Value列を削除
    if 'Trigger_Value' in df_deduplicated.columns:
        df_deduplicated = df_deduplicated.drop(columns=['Trigger_Value'])
        print("Trigger_Value列を削除しました")
    
    # 出力ファイル名が指定されていない場合は入力ファイルを上書き
    if output_file is None:
        output_file = input_file
    
    # 結果を保存
    df_deduplicated.to_csv(output_file, index=False)
    print(f"結果を保存しました: {output_file}\n")


def main():
    parser = argparse.ArgumentParser(
        description='トリガーCSVファイルから連続する重複トリガーを削除し、Trigger_Value列を削除します。'
    )
    parser.add_argument(
        'target_directory',
        type=Path,
        help='処理対象のCSVファイルが含まれるディレクトリパス'
    )
    
    args = parser.parse_args()
    target_dir = args.target_directory
    
    # ディレクトリの存在確認
    if not target_dir.exists():
        print(f"エラー: ディレクトリが見つかりません: {target_dir}")
        return 1
    
    if not target_dir.is_dir():
        print(f"エラー: 指定されたパスはディレクトリではありません: {target_dir}")
        return 1
    
    # ディレクトリ内のすべての.csvファイルを取得
    csv_files = sorted(target_dir.glob("*.csv"))
    
    if not csv_files:
        print(f"警告: ディレクトリ内にCSVファイルが見つかりません: {target_dir}")
        return 0
    
    print(f"トリガーファイルの重複削除を開始します\n")
    print(f"対象ディレクトリ: {target_dir}")
    print(f"処理対象ファイル数: {len(csv_files)}\n")
    
    # 各ファイルを処理
    processed_count = 0
    for csv_file in csv_files:
        print(f"処理中: {csv_file.name}")
        try:
            deduplicate_triggers(str(csv_file))
            processed_count += 1
        except Exception as e:
            print(f"エラー: {csv_file.name} の処理中にエラーが発生しました - {e}\n")
            continue
    
    print(f"完了: {processed_count}/{len(csv_files)} ファイルを処理しました")
    return 0

if __name__ == "__main__":
    exit(main())
