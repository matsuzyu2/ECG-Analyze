#!/usr/bin/env python3
"""
仮想トリガー挿入プログラム

追加対象のファイルに対して、追加元のファイルからトリガーを補完し、
アノテーションを追加する。

使用方法:
    python3 insert_virtual_triggers.py <追加元のファイル> <基準となる行数:追加したいトリガーまでを指定> \
        <追加対象のファイル> <基準となる行数>

例:
    python3 insert_virtual_triggers.py source.csv 3:10 target.csv 5
"""

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path


def parse_timestamp(ts_str):
    """
    タイムスタンプ文字列をdatetimeオブジェクトに変換
    複数のフォーマットに対応
    """
    formats = [
        "%Y-%m-%dT%H:%M:%S.%f",  # ISO format with microseconds
        "%Y-%m-%d %H:%M:%S.%f",  # Space separated with microseconds
        "%Y-%m-%d %H:%M:%S",     # Space separated without microseconds
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            continue
    
    raise ValueError(f"タイムスタンプの解析に失敗しました: {ts_str}")


def format_timestamp_like(dt, reference_str):
    """
    参照文字列と同じフォーマットでdatetimeをフォーマット
    """
    if 'T' in reference_str:
        # ISO format
        if '.' in reference_str:
            return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")
        else:
            return dt.strftime("%Y-%m-%dT%H:%M:%S")
    else:
        # Space separated
        if '.' in reference_str:
            return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # ミリ秒まで
        else:
            return dt.strftime("%Y-%m-%d %H:%M:%S")


def read_trigger_file(file_path):
    """
    トリガーファイルを読み込む
    返り値: (header, triggers)
        header: ヘッダー行のリスト
        triggers: [{"timestamp": str, "annotation": str, "original_line": str}, ...]
    """
    triggers = []
    header = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        # ヘッダーの正規化（大文字小文字を統一）
        if reader.fieldnames is None:
            raise ValueError(f"CSVファイルにヘッダーが見つかりません: {file_path}")
        
        header = reader.fieldnames
        fieldnames = [name.lower().strip() for name in reader.fieldnames]
        
        for row in reader:
            # キーを正規化
            normalized_row = {k.lower().strip(): v for k, v in row.items()}
            
            # タイムスタンプフィールドを探す
            timestamp = normalized_row.get('timestamp', '')
            annotation = normalized_row.get('annotation', '')
            
            triggers.append({
                'timestamp': timestamp,
                'annotation': annotation,
                'original_row': row
            })
    
    return header, triggers


def insert_virtual_triggers(target_file, target_base_line, source_file, 
                            source_base_line, source_end_line):
    """
    仮想トリガーを挿入
    
    Args:
        target_file: 追加対象のファイルパス
        target_base_line: 追加対象の基準行番号（ヘッダー含む1-indexed、1=ヘッダー行）
        source_file: 追加元のファイルパス
        source_base_line: 追加元の基準行番号（ヘッダー含む1-indexed、1=ヘッダー行）
        source_end_line: 追加元の終了行番号（ヘッダー含む1-indexed）
    """
    # ファイルを読み込む
    print(f"追加対象ファイルを読み込み: {target_file}")
    target_header, target_triggers = read_trigger_file(target_file)
    
    print(f"追加元ファイルを読み込み: {source_file}")
    source_header, source_triggers = read_trigger_file(source_file)
    
    # 行番号の検証（ヘッダー含む）
    # 行1 = ヘッダー、行2以降 = データ行
    total_target_lines = len(target_triggers) + 1  # ヘッダー + データ行
    total_source_lines = len(source_triggers) + 1
    
    if target_base_line < 2 or target_base_line > total_target_lines:
        raise ValueError(f"追加対象の基準行番号が範囲外です: {target_base_line} "
                        f"(2-{total_target_lines}、行1はヘッダー行)")
    
    if source_base_line < 2 or source_base_line > total_source_lines:
        raise ValueError(f"追加元の基準行番号が範囲外です: {source_base_line} "
                        f"(2-{total_source_lines}、行1はヘッダー行)")
    
    if source_end_line < source_base_line or source_end_line > total_source_lines:
        raise ValueError(f"追加元の終了行番号が範囲外です: {source_end_line} "
                        f"(2-{total_source_lines}、行1はヘッダー行)")
    
    # データ行のインデックスに変換（ヘッダー行を除く）
    target_data_idx = target_base_line - 2  # 行2 → インデックス0
    source_base_idx = source_base_line - 2
    source_end_idx = source_end_line - 2
    
    # タイムスタンプのフォーマットを取得
    target_base_ts_str = target_triggers[target_data_idx]['timestamp']
    
    # 基準となるタイムスタンプを取得
    target_base_ts = parse_timestamp(target_base_ts_str)
    source_base_ts = parse_timestamp(source_triggers[source_base_idx]['timestamp'])
    
    print(f"\n基準トリガー情報:")
    print(f"  追加対象 (行{target_base_line}): {target_base_ts_str} - "
          f"{target_triggers[target_data_idx]['annotation']}")
    print(f"  追加元 (行{source_base_line}): {source_triggers[source_base_idx]['timestamp']} - "
          f"{source_triggers[source_base_idx]['annotation']}")
    
    # 仮想トリガーを作成（基準行は除外し、次の行から挿入）
    virtual_triggers = []
    print(f"\n仮想トリガーを作成中 (行{source_base_line + 1}から行{source_end_line}まで):")
    
    for line_num in range(source_base_line + 1, source_end_line + 1):
        data_idx = line_num - 2  # データ行のインデックス
        source_trigger = source_triggers[data_idx]
        source_ts = parse_timestamp(source_trigger['timestamp'])
        
        # 追加元での基準トリガーからのずれを計算
        time_offset = source_ts - source_base_ts
        
        # 追加対象のタイムスタンプに適用
        new_ts = target_base_ts + time_offset
        new_ts_str = format_timestamp_like(new_ts, target_base_ts_str)
        
        virtual_trigger = {
            'timestamp': new_ts_str,
            'annotation': source_trigger['annotation'],
            'source_line': line_num
        }
        virtual_triggers.append(virtual_trigger)
        
        print(f"  行{line_num}: {new_ts_str} - {source_trigger['annotation']} "
              f"(offset: {time_offset})")
    
    # 基準行の次に仮想トリガーを挿入
    # target_data_idxは基準行のデータ配列内インデックス（0-indexed）
    # 基準行の次に挿入するため、target_data_idx + 1の位置に挿入
    output_triggers = (
        target_triggers[:target_data_idx + 1] +  # 基準行まで
        virtual_triggers +                        # 仮想トリガー
        target_triggers[target_data_idx + 1:]     # 基準行の次以降
    )
    
    # 出力ファイル名を生成（短縮版）
    output_file = Path(target_file).parent / (Path(target_file).stem + "_vtrg.csv")
    
    print(f"\n結果を保存中: {output_file}")
    
    # ヘッダーは既に読み込み済み
    header = target_header
    
    # 正規化されたヘッダー名を元のケースにマッピング
    header_map = {}
    for h in header:
        header_map[h.lower().strip()] = h
    
    # CSVファイルとして保存
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        
        for trigger in output_triggers:
            row = []
            for h in header:
                key = h.lower().strip()
                if key == 'timestamp':
                    row.append(trigger['timestamp'])
                elif key == 'annotation':
                    row.append(trigger['annotation'])
                elif key == 'trigger_value' and 'original_row' in trigger:
                    # 元のファイルに trigger_value がある場合は保持
                    row.append(trigger['original_row'].get('trigger_value', '100'))
                elif key == 'trigger_value':
                    # 仮想トリガーの場合はデフォルト値
                    row.append('100')
                else:
                    # その他のフィールド
                    if 'original_row' in trigger:
                        row.append(trigger['original_row'].get(h, ''))
                    else:
                        row.append('')
            writer.writerow(row)
    
    print(f"\n完了!")
    print(f"  元のトリガー数: {len(target_triggers)}")
    print(f"  追加されたトリガー数: {len(virtual_triggers)}")
    print(f"  合計トリガー数: {len(output_triggers)}")
    print(f"  出力ファイル: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='仮想トリガーを挿入するプログラム',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python3 insert_virtual_triggers.py source.csv 3:10 target.csv 5
    → source.csvの3行目から10行目までのトリガーを、target.csvの5行目を基準に追加

  python3 insert_virtual_triggers.py source.csv 1:20 target.csv 1
    → source.csvの1行目から20行目までのトリガーを、target.csvの1行目を基準に追加
        """
    )
    
    parser.add_argument('source_file', help='追加元のファイル')
    parser.add_argument('source_lines', 
                       help='追加元の基準行と終了行（例: 3:10）')
    parser.add_argument('target_file', help='追加対象のファイル')
    parser.add_argument('target_base_line', type=int, 
                       help='追加対象の基準となる行番号（1から開始）')
    
    args = parser.parse_args()
    
    # source_linesをパース
    try:
        source_base_line, source_end_line = map(int, args.source_lines.split(':'))
    except ValueError:
        print(f"エラー: source_linesの形式が不正です: {args.source_lines}", 
              file=sys.stderr)
        print("正しい形式: 開始行:終了行（例: 3:10）", file=sys.stderr)
        sys.exit(1)
    
    # ファイルの存在確認
    if not Path(args.target_file).exists():
        print(f"エラー: 追加対象ファイルが見つかりません: {args.target_file}", 
              file=sys.stderr)
        sys.exit(1)
    
    if not Path(args.source_file).exists():
        print(f"エラー: 追加元ファイルが見つかりません: {args.source_file}", 
              file=sys.stderr)
        sys.exit(1)
    
    try:
        insert_virtual_triggers(
            args.target_file,
            args.target_base_line,
            args.source_file,
            source_base_line,
            source_end_line
        )
    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
