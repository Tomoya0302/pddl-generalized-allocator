from typing import List
import re

def tokenize(text: str) -> List[str]:
    """
    PDDLテキストをトークン列に変換。
    - '(' , ')' は単独トークン
    - ホワイトスペースで分割
    - ';' で始まるコメント行を削除
    """
    # コメント行を削除
    lines = text.split('\n')
    clean_lines = []
    for line in lines:
        comment_pos = line.find(';')
        if comment_pos >= 0:
            line = line[:comment_pos]
        clean_lines.append(line)
    
    clean_text = '\n'.join(clean_lines)
    
    # '(' と ')' を前後にスペース挿入
    clean_text = re.sub(r'([()])', r' \1 ', clean_text)
    
    # スペースで分割してトークンリストに
    tokens = clean_text.split()
    
    # 空文字列を除去
    tokens = [t for t in tokens if t.strip()]
    
    return tokens