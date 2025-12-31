#!/usr/bin/env python3
"""
アノテーションファイルに従ってCSVファイルを分割するプログラム

使用例:
    python3 split_by_annotation.py <分割対象ファイル> <アノテーションファイル>
    
    例:
    python3 split_by_annotation.py data.csv annotation.csv
"""

import pandas as pd
import sys
from pathlib import Path
from typing import Tuple, Optional


# 分割対象のアノテーションペア（Start/End）
ANNOTATION_PAIRS = [
    ("GoNoGo_Baseline_Practice_Start", "GoNoGo_Baseline_Practice_End"),
    ("GoNoGo_Baseline_Start", "GoNoGo_Baseline_End"),
    ("Resting_HR_1_Set1_Start", "Resting_HR_1_Set1_End"),
    ("Session_Start", "Session_Stop"),
    ("Resting_HR_2_Set1_Start", "Resting_HR_2_Set1_End"),
    ("GoNoGo_Set1_Start", "GoNoGo_Set1_End"),
    ("Resting_HR_1_Set2_Start", "Resting_HR_1_Set2_End"),
    ("Resting_HR_2_Set2_Start", "Resting_HR_2_Set2_End"),
    ("GoNoGo_Set2_Start", "GoNoGo_Set2_End"),
]


def read_csv_with_metadata_skip(file_path: str) -> pd.DataFrame:
    """
    CSVファイルを読み込む際、先頭のメタデータ行を自動的にスキップする
    
    Args:
        file_path: 読み込むCSVファイルのパス
        
    Returns:
        読み込まれたDataFrame
    """
    # まず先頭数行を読んで、どこからデータが始まるかを判定
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = [f.readline() for _ in range(10)]
    
    skip_rows = 0
    for i, line in enumerate(lines):
        # カンマ区切りのヘッダー行を探す
        # "Time (s)" や "Timestamp" などの典型的なヘッダーを含む行を探す
        if 'Timestamp' in line or 'Time (s)' in line:
            skip_rows = i
            break
    
    # データを読み込む
    if skip_rows > 0:
        print(f"  メタデータ行を検出: {skip_rows}行をスキップします")
        df = pd.read_csv(file_path, skiprows=skip_rows)
    else:
        df = pd.read_csv(file_path)
    
    return df


def find_all_timestamps_for_annotations(
    df_annotation: pd.DataFrame, start_annotation: str, end_annotation: str
) -> list[Tuple[str, str]]:
    """
    指定されたアノテーションペアのタイムスタンプを全て取得する
    
    Args:
        df_annotation: アノテーションDataFrame
        start_annotation: 開始アノテーション名
        end_annotation: 終了アノテーション名
        
    Returns:
        [(start_timestamp, end_timestamp), ...] のリスト
        見つからない場合は空リスト
    """
    start_rows = df_annotation[df_annotation['Annotation'] == start_annotation]
    end_rows = df_annotation[df_annotation['Annotation'] == end_annotation]
    
    if start_rows.empty or end_rows.empty:
        return []
    
    # 各開始アノテーションに対応する終了アノテーションを見つける
    result = []
    for _, start_row in start_rows.iterrows():
        start_timestamp = start_row['Timestamp']
        
        # この開始タイムスタンプより後の終了アノテーションを探す
        matching_end = end_rows[end_rows['Timestamp'] > start_timestamp]
        
        if not matching_end.empty:
            # 最初に見つかった終了アノテーションを使用
            end_timestamp = matching_end.iloc[0]['Timestamp']
            result.append((start_timestamp, end_timestamp))
    
    return result


def split_csv_by_annotations(target_file: str, annotation_file: str) -> None:
    """
    アノテーションファイルに従ってCSVファイルを分割する
    
    Args:
        target_file: 分割対象のCSVファイル
        annotation_file: アノテーション情報を含むCSVファイル
    """
    # ファイルを読み込む
    print(f"分割対象ファイル: {target_file}")
    print(f"アノテーションファイル: {annotation_file}")
    print()
    
    # メタデータ行の検出とスキップ
    # ファイルの先頭数行をチェックして、メタデータ行をスキップする
    df_target = read_csv_with_metadata_skip(target_file)
    df_annotation = read_csv_with_metadata_skip(annotation_file)
    
    print(f"分割対象ファイルの行数: {len(df_target)}")
    print(f"アノテーションファイルの行数: {len(df_annotation)}")
    print()
    
    # カラム確認
    if 'Timestamp' not in df_target.columns:
        raise ValueError(f"分割対象ファイルに Timestamp 列が見つかりません: {target_file}")
    if 'Timestamp' not in df_annotation.columns or 'Annotation' not in df_annotation.columns:
        raise ValueError(f"アノテーションファイルに必要な列が見つかりません: {annotation_file}")
    
    # 出力ディレクトリの準備
    target_path = Path(target_file)
    output_dir = target_path.parent / "split_segments"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"出力ディレクトリ: {output_dir}")
    print()
    
    # 各アノテーションペアについて分割処理
    split_count = 0
    for idx, (start_annotation, end_annotation) in enumerate(ANNOTATION_PAIRS, 1):
        print(f"[{idx}/{len(ANNOTATION_PAIRS)}] {start_annotation} → {end_annotation}")
        
        # アノテーションのタイムスタンプを全て取得
        timestamp_pairs = find_all_timestamps_for_annotations(
            df_annotation, start_annotation, end_annotation
        )
        
        if not timestamp_pairs:
            print(f"  ⚠ アノテーションが見つかりませんでした。スキップします。")
            print()
            continue
        
        # 複数の出現がある場合、それぞれを別ファイルとして保存
        occurrence_count = len(timestamp_pairs)
        print(f"  検出された出現回数: {occurrence_count}")
        
        for occurrence_idx, (start_ts, end_ts) in enumerate(timestamp_pairs, 1):
            if occurrence_count > 1:
                print(f"  [{occurrence_idx}/{occurrence_count}]")
            
            print(f"    開始タイムスタンプ: {start_ts}")
            print(f"    終了タイムスタンプ: {end_ts}")
            
            # 分割対象ファイルから該当する範囲を抽出
            df_segment = df_target[
                (df_target['Timestamp'] >= start_ts) & 
                (df_target['Timestamp'] <= end_ts)
            ]
            
            if df_segment.empty:
                print(f"    ⚠ 該当するデータが見つかりませんでした。スキップします。")
                print()
                continue
            
            print(f"    抽出行数: {len(df_segment)}")
            
            # ファイル名を生成（セグメント番号_アノテーション名_出現回数.csv）
            segment_name = start_annotation.replace("_Start", "")
            
            # 複数の出現がある場合は連番を追加
            if occurrence_count > 1:
                output_filename = f"{idx:02d}_{segment_name}_{occurrence_idx:02d}.csv"
            else:
                output_filename = f"{idx:02d}_{segment_name}.csv"
            
            output_path = output_dir / output_filename
            
            # CSVファイルとして保存
            df_segment.to_csv(output_path, index=False)
            print(f"    ✓ 保存: {output_path}")
            
            split_count += 1
        
        print()
    
    print(f"完了: {split_count} 個のセグメントを分割しました。")


def main():
    """メイン関数"""
    if len(sys.argv) != 3:
        print("使用方法: python3 split_by_annotation.py <分割対象ファイル> <アノテーションファイル>")
        print()
        print("例:")
        print("  python3 split_by_annotation.py data.csv annotation.csv")
        sys.exit(1)
    
    target_file = sys.argv[1]
    annotation_file = sys.argv[2]
    
    # ファイルの存在確認
    if not Path(target_file).exists():
        print(f"エラー: 分割対象ファイルが見つかりません: {target_file}")
        sys.exit(1)
    
    if not Path(annotation_file).exists():
        print(f"エラー: アノテーションファイルが見つかりません: {annotation_file}")
        sys.exit(1)
    
    try:
        split_csv_by_annotations(target_file, annotation_file)
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
