#!/usr/bin/env python3
"""
TRIGGER(DIGITAL)の値が0から57344に変化した行のTimestampを検出するプログラム

使用方法:
    python3 detect_trigger_changes.py <input_csv>
"""

import pandas as pd
import argparse
import os
import re
from pathlib import Path


def detect_trigger_changes(input_file: str, output_file: str, target_value: int = 57344):
    """
    TRIGGER(DIGITAL)の値が0から指定値に変化した行のTimestampを検出
    
    Args:
        input_file: 入力CSVファイルのパス
        output_file: 出力CSVファイルのパス
        target_value: 検出するトリガー値（デフォルト: 57344）
    """
    print(f"入力ファイル: {input_file}")
    print(f"出力ファイル: {output_file}")
    print(f"検出するトリガー値: 0 → {target_value}")
    print()
    
    # CSVファイルを読み込む（最初の4行はヘッダー情報なのでスキップ）
    print("CSVファイルを読み込んでいます...")
    df = pd.read_csv(input_file, skiprows=4)
    
    print(f"総行数: {len(df):,} 行")
    print(f"列名: {', '.join(df.columns)}")
    print()
    
    # TRIGGER(DIGITAL)列が存在することを確認
    trigger_column = 'TRIGGER(DIGITAL)'
    if trigger_column not in df.columns:
        raise ValueError(f"列 '{trigger_column}' が見つかりません。")
    
    # TRIGGER(DIGITAL)の値が0から57344に変化した行を検出
    print("トリガー変化を検出しています...")
    
    # 前の行のトリガー値を取得（最初の行はNaN）
    df['prev_trigger'] = df[trigger_column].shift(1)
    
    # 0から57344に変化した行を抽出
    trigger_changes = df[
        (df['prev_trigger'] == 0) & 
        (df[trigger_column] == target_value)
    ]
    
    print(f"検出された変化: {len(trigger_changes)} 件")
    print()
    
    if len(trigger_changes) == 0:
        print("警告: トリガー値の変化が検出されませんでした。")
        print("データの確認:")
        print(f"  TRIGGER(DIGITAL)のユニーク値: {sorted(df[trigger_column].unique())}")
        print()
    
    # Timestampを抽出して結果を保存
    result_df = trigger_changes[['Timestamp']].copy()
    result_df = result_df.reset_index(drop=True)
    
    # 出力ディレクトリが存在しない場合は作成
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # CSVファイルとして出力（インデックスなし）
    result_df.to_csv(output_file, index=False)
    print(f"結果を保存しました: {output_file}")
    print()
    
    # 結果のプレビューを表示
    if len(result_df) > 0:
        print("検出されたトリガー変化:")
        print(result_df.to_string())
    
    return result_df


def main():
    parser = argparse.ArgumentParser(
        description='TRIGGER(DIGITAL)の値が0から57344に変化した行のTimestampを検出します。'
    )
    parser.add_argument(
        'input_file',
        type=Path,
        help='入力CSVファイルのパス'
    )
    parser.add_argument(
        '--target-value',
        type=int,
        default=57344,
        help='検出するトリガー値（デフォルト: 57344）'
    )
    
    args = parser.parse_args()
    
    # ファイルの存在確認
    if not args.input_file.exists():
        print(f"エラー: 入力ファイルが見つかりません: {args.input_file}")
        return 1
    
    # 出力ファイル名を自動生成（短縮版）
    # ファイル名末尾の数字パターン（_01, _02など）を削除
    cleaned_stem = re.sub(r'_ext$', '', args.input_file.stem)
    output_file = args.input_file.parent / f"{cleaned_stem}_trg.csv"
    
    try:
        detect_trigger_changes(str(args.input_file), str(output_file), args.target_value)
        return 0
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
