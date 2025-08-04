import re
from dataclasses import dataclass

@dataclass
class Patterns:
    # Основной паттерн для матерных слов (с учетом замен символов)
    profanity_pattern = re.compile(
        r'\b([хx][уyю][йjеёи]|[пp][иеi][з3z][дd]|[б6][лl][яaа@]|[её][б6][аaа@]'
        r'|[сc][уy][кk][аaа@]|[мm][уy][дd][аaа@кk]|[гg][аa][вv][нn][оo0]'
        r'|[пp][иi][дd][аaоo][рr][аaоo]|[з3z][аa][еe][б6][аa]|[оo0][тt][ъь]?[еeё][б6]'
        r'|[дd][еe][б6][иi][лl]|[дd][уy][рr][аa][кk]|[ч4][мm][оo0]|[шs][лl][юu][хxh]'
        r'|[пp][оo0][сc][рr][аa][тtь]|[мm][аa][нn][дd][аa]|[еeё][б6][аa][лl]'
        r'|[вv][ыy][еeё][б6][аa])\w*\b', flags=re.IGNORECASE)
    
    # Дополнительные паттерны для сложных случаев
    additional_patterns = [
        r'\b[аa][хxh][уy][еeё][лlтt]\w*\b',
        r'\b[пp][иi][з3z][дd][аaоo][кkцc]\w*\b',
        r'\b[хxh][уy][йj][лl][оo0]\b',
        r'\b[сc][уy][ч4][кk][аaиi]\w*\b',
        r'\b[мm][аa][тt][ь]\b',
        r'\b[оo0][тt][пp][иi][з3z][дd]\w*\b',
        r'\b[з3z][аa][пp][иi][з3z][дd]\w*\b',
        r'\b[нn][еe][вv][рr][оo0][тt][еe][б6]\w*\b',
        r'\b[гg][аa][нn][дd][оo0][нn]\w*\b',
        r'\b[гg][аaа@á][нn][дd][оo0][нn]\w*\b']
