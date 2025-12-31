#!/usr/bin/env python3
"""
CSVファイルにannotation列を追加するプログラム

使用例:
    # 100行目から、target.csvにsource.csvのannotation列を追加
    python3 add_annotation.py source.csv target.csv 100
    
    # 2行目から追加
    python3 add_annotation.py source.csv target.csv 2
    
    # 絶対パスで指定
    python3 add_annotation.py /path/to/source.csv /path/to/target.csv 2
"""

import pandas as pd
import sys


def add_annotation(start_index: int, target_file: str, source_file: str) -> None:
    """
    追加元ファイルからannotation列を抽出し、追加対象ファイルの指定行から追加する
    
    Args:
        start_index: annotation列を追加開始する行のインデックス（0始まり、内部用）
        target_file: annotation列を追加する対象のCSVファイル
        source_file: annotation列を抽出する元のCSVファイル
    """
    # ファイルを読み込む
    df_target = pd.read_csv(target_file)
    df_source = pd.read_csv(source_file)
    
    print(f"追加対象ファイル: {target_file} ({len(df_target)} 行)")
    print(f"追加元ファイル: {source_file} ({len(df_source)} 行)")
    print(f"追加開始行: {start_index + 2} 行目")
    
    # annotation列の存在確認（大文字小文字を区別しない）
    annotation_col = None
    for col in df_source.columns:
        if col.lower() == 'annotation':
            annotation_col = col
            break
    
    if annotation_col is None:
        raise ValueError(f"追加元ファイルにannotation列が見つかりません: {source_file}")
    
    # インデックスの妥当性チェック
    if start_index < 0 or start_index >= len(df_target):
        raise ValueError(f"インデックスが範囲外です: {start_index} (対象ファイルの行数: {len(df_target)})")
    
    # annotation列がない場合は作成
    if 'Annotation' not in df_target.columns:
        df_target['Annotation'] = None
    
    # annotation列を追加
    end_index = start_index + len(df_source)
    if end_index > len(df_target):
        print(f"警告: 追加元のデータが対象ファイルの残り行数を超えています")
        end_index = len(df_target)
    
    # 指定されたインデックスから、annotation列の値を設定
    df_target.loc[start_index:end_index-1, 'Annotation'] = df_source[annotation_col].values[:end_index-start_index]
    
    # 結果を保存（元のファイルを上書き）
    df_target.to_csv(target_file, index=False)
    
    print(f"✓ Annotation列を追加しました: {start_index + 2} ~ {end_index + 1} 行目")
    print(f"✓ 結果を保存しました: {target_file}")


def main():
    # コマンドライン引数のチェック
    if len(sys.argv) != 4:
        print("使用法: python3 add_annotation.py <追加元のファイル> <追加対象のファイル> <行数>")
        print()
        print("例:")
        print("  python3 add_annotation.py source.csv target.csv 100")
        sys.exit(1)
    
    # 引数を取得
    try:
        source_file = sys.argv[1]
        target_file = sys.argv[2]
        start_line = int(sys.argv[3])
    except ValueError:
        print("エラー: 行数は整数で指定してください")
        sys.exit(1)
    
    # 行数の妥当性チェック（ヘッダー行を考慮）
    if start_line < 2:
        print("エラー: 行数は2以上を指定してください（1行目はヘッダー）")
        sys.exit(1)
    
    # 行数をインデックスに変換（ヘッダー行を考慮：ファイルの行数 → データのインデックス）
    start_index = start_line - 2
    
    # 処理実行
    try:
        add_annotation(start_index, target_file, source_file)
    except Exception as e:
        print(f"エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
