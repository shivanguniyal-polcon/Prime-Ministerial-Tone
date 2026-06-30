#!/usr/bin/env python3
import os
import re
import sys
import json
import fitz
from pathlib import Path

# ocr fixes because government scanners are garbage
SUFFIXES = [
    (r'(\w+)ti on\b', r'\1tion'), (r'(\w+)si on\b', r'\1sion'),
    (r'(\w+)o us\b', r'\1ous'),   (r'(\w+)t or\b', r'\1tor'),
    (r'(\w+)a in\b', r'\1ain'),   (r'(\w+)o me\b', r'\1ome'),
    (r'(\w+)m on\b', r'\1mon'),
]

FUSED = {
    'afirst': 'a first', 'alarge': 'a large', 'aclear': 'a clear', 'asober': 'a sober',
    'aprey': 'a prey', 'ameans': 'a means', 'anote': 'a note', 'abit': 'a bit',
    'amuch': 'a much', 'awhile': 'a while', 'avital': 'a vital', 'ahigh': 'a high',
    'acopy': 'a copy', 'aview': 'a view', 'ajoint': 'a joint', 'agood': 'a good',
    'agreat': 'a great', 'ayear': 'a year', 'anew': 'a new', 'acreed': 'a creed',
    'aman': 'a man', 'adak': 'a dak', 'areal': 'a real', 'afew': 'a few',
    'awhole': 'a whole', 'aword': 'a word', 'acoy': 'a coy', 'aplanor': 'a plan or',
    'avery': 'a very', 'whatis': 'what is', 'neededis': 'needed is', 'producedin': 'produced in',
    'concentrateon': 'concentrate on', 'withit': 'with it', 'thatit': 'that it', 'lateron': 'later on',
    'stayin': 'stay in', 'officersor': 'officers or', 'impedimentin': 'impediment in',
    'problemis': 'problem is', 'solvedor': 'solved or', 'achievedin': 'achieved in',
    'oneor': 'one or', 'thinkin': 'think in', 'floodsor': 'floods or', 'ayearor': 'a year or',
    'Whateverit': 'Whatever it', 'Statesor': 'States or', 'thisin': 'this in', 'believein': 'believe in',
    'workedit': 'worked it', 'aboutit': 'about it', 'peacein': 'peace in', 'hereis': 'here is',
    'whois': 'who is', 'succeedin': 'succeed in', 'andin': 'and in', 'forit': 'for it',
    'wasin': 'was in', 'Gandhijior': 'Gandhiji or', 'Whatis': 'What is', 'happeningor': 'happening or',
    'happenedin': 'happened in', 'Marxin': 'Marx in', 'andit': 'and it', 'saidin': 'said in',
    'letus': 'let us', 'Letus': 'Let us', 'Letme': 'Let me', 'Khrushchevis': 'Khrushchev is',
    'theoryin': 'theory in', 'walkon': 'walk on', 'becausein': 'because in', 'workon': 'work on',
    'dragin': 'drag in', 'followin': 'follow in', 'footstepsin': 'footsteps in', 'Congressin': 'Congress in',
    'arrangeit': 'arrange it', 'indulgein': 'indulge in', 'raidersin': 'raiders in',
    'authoritiesin': 'authorities in', 'situationin': 'situation in', 'Kashmiris': 'Kashmir is',
    'freedomis': 'freedom is', 'Kutchor': 'Kutch or', 'possiblein': 'possible in', 'areply': 'a reply',
    'takeit': 'take it', 'agreementon': 'agreement on', 'hostilitiesin': 'hostilities in',
    'fromus': 'from us', 'sentme': 'sent me', 'placedon': 'placed on', 'Nationsin': 'Nations in',
    'sheis': 'she is', 'thereafteris': 'thereafter is', 'stateon': 'state on', 'aggressionon': 'aggression on',
    'carryon': 'carry on', 'peoplein': 'people in', 'freedomor': 'freedom or', "Khan'spress": "Khan's press",
    'thisis': 'this is', 'welcomeit': 'welcome it', 'belatedit': 'belated it', 'experienceis': 'experience is',
    'followedit': 'followed it', 'Indiain': 'India in', 'subsequentlyin': 'subsequently in',
    'chapterin': 'chapter in', 'countryis': 'country is', 'madein': 'made in', 'satisfactoryor': 'satisfactory or',
    'saidit': 'said it', 'tackleit': 'tackle it', 'resolveit': 'resolve it', 'herein': 'here in',
    'aweekor': 'a week or', 'agreementis': 'agreement is', 'implementit': 'implement it', 'viewin': 'view in',
    'difficultiesin': 'difficulties in', 'placein': 'place in', 'Burmais': 'Burma is', 'Kathmanduin': 'Kathmandu in',
    'Indiais': 'India is', 'Ofcourse': 'Of course', 'canin': 'can in', 'thatin': 'that in',
    'beginningit': 'beginning it', 'frequentlyon': 'frequently on', 'conflictsor': 'conflicts or',
    'occuron': 'occur on', 'describedit': 'described it', 'thingsin': 'things in', 'commenceon': 'commence on',
    "other'spoint": "other's point", 'decisionin': 'decision in', 'substantiallyin': 'substantially in',
    'invitedme': 'invited me', 'Burmaon': 'Burma on', 'Indiaon': 'India on', 'withme': 'with me',
    'worldin': 'world in', 'thinkit': 'think it', 'forus': 'for us', 'todayon': 'today on',
    'spendon': 'spend on', 'wereit': 'were it', 'ownon': 'own on', 'alsoin': 'also in',
    'Thereis': 'There is', 'whereon': 'where on', 'alsoon': 'also on', 'strengthis': 'strength is',
    'Ceylonis': 'Ceylon is', 'milli on': 'million', 'ltold': 'I told', 'tous': 'to us',
    'I shell': 'I shall', 'tome': 'to me', 'butit': 'but it', 'Butit': 'But it',
    'manin': 'man in', 'forme': 'for me', 'Forme': 'For me', 'summ it': 'summit',
    'beca me': 'became', 'pers on': 'person', 'fashi on': 'fashion', "Gandhiji'stime": "Gandhiji's time",
    'outor': 'out or', 'Governmentor': 'Government or', 'expertor': 'expert or', 'wheator': 'wheat or',
    'do itor': 'do it or', 'rightor': 'right or', 'responsibilityin': 'responsibility in', 'getit': 'get it',
    'eyeon': 'eye on', 'notin': 'not in', 'sayin': 'say in', 'hasin': 'has in', 'yetit': 'yet it',
    'hadin': 'had in', 'In dia': 'India', 'P ak ist an': 'Pakistan', 'pr od u ction': 'production',
    'resp on si bi l it y': 'responsibility', 'op i ni on': 'opinion', 'bet ween': 'between',
    'comi ng': 'coming', 'fr om': 'from'
}

SWAPS = {
    r'\breplying lo\b': 'replying to', r'\bmight he able\b': 'might be able',
    r'\bwe fell that\b': 'we felt that', r'\bI fell that\b': 'I felt that',
    r'\bcome pressure\b': 'some pressure', r'\bhand it aver\b': 'hand it over',
    r'\baver to\b': 'over to', r'\bOne thins has\b': 'One thing has',
    r'\btonne- respectively\b': 'tonnes respectively', r'\badds upto\b': 'adds up to',
    r'\b1 greatly\b': 'I greatly', r'\bltold\b': 'I told', r'\b1 have\b': 'I have',
    r"At that' time": 'At that time', r'\bail the\b': 'all the',
    r'bringing; about': 'bringing about', r'note find of': 'note and of',
    r'were it act for': 'were it not for', r'\bareain\b': 'area in',
    r'\bto proved to\b': 'to proceed to', r'\bto be repeated again\b': 'to be repeated again'
}

DATE_RE = re.compile(
    r'^\s*(?:New Delhi\s*,?\s*)?(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|'
    r'September|October|November|December)\w*\s*,?\s*\d{4})\s*$',
    re.M | re.I
)

def read_pdf(path):
    try:
        doc = fitz.open(path)
    except:
        return ""

    lines = []
    for page in doc:
        h = page.rect.height
        w = page.rect.width
        for b in page.get_text("dict")["blocks"]:
            if b["type"] == 1: # skip images
                continue
            for ln in b["lines"]:
                x0, y0, x1, y1 = ln["bbox"]
                # drop headers/footers
                if y1 < h * 0.06 or y0 > h * 0.94:
                    continue
                # drop marginalia
                if (x1 - x0) < w * 0.15 and (x0 < w * 0.05 or x1 > w * 0.95):
                    continue

                text = "".join(s["text"] for s in ln["spans"]).strip()
                if text:
                    lines.append(text)
    doc.close()
    return "\n".join(lines)

def strip_garbage(text):
    out = []
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        if re.match(r'^\d{1,3}\s*\d{0,3}$', line): continue
        if re.match(r'^\(?[ivxlc]+\)?$', line, re.I): continue
        if re.match(r'^xxx\d*$', line, re.I): continue
        if line.upper() in ["CONTENTS", "PREFACE", "SL. YEAR/DATE SUBJECT", "NO.", "PAGE NO.", "NIL"]: continue
        if re.match(r'^\d{1,3}\.$', line): continue
        if '|' in line and re.search(r'(Sl\.|No\.|Page|Subject|Contents)', line, re.I): continue
        if re.match(r'^.*\|.*\|.*$', line) and len(line) < 100: continue
        if re.match(r'^\*{1,3}\s*(Replying to|Responding to)', line): continue
        out.append(line)
    return "\n".join(out)

def fix_text(text):
    for pat, rep in SUFFIXES:
        text = re.sub(pat, rep, text)

    for bad, good in FUSED.items():
        text = re.sub(r'\b' + re.escape(bad) + r'\b', good, text, flags=re.I)

    for pat, rep in SWAPS.items():
        text = re.sub(pat, rep, text)

    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    text = text.replace('Secretary- General', 'Secretary-General')
    text = re.sub(r'a\.m\.\s*on\s*at\s*3:30\s*', '', text)
    text = re.sub(r'\s+', ' ', text).strip()

    # block stutters (scanners sometimes duplicate entire blocks)
    words = text.split()
    out = []
    i = 0
    n = len(words)
    while i < n:
        found = 0
        for sz in range(15, min(41, n - i)):
            if i + 2 * sz <= n and words[i:i+sz] == words[i+sz:i+2*sz]:
                out.extend(words[i:i+sz])
                i += 2 * sz
                found = 1
                break
        if not found:
            out.append(words[i])
            i += 1

    text = " ".join(out)

    sentences = re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) >= 2 and sentences[-1].strip() == sentences[-2].strip():
        sentences.pop()

    return " ".join(sentences)

def segment(text):
    toc = re.search(r'(?:MOTION\s+OF|STATEMENT\s+REGARDING|NO-CONFIDENCE\s+MOTION|MOTION\s+REGARDING|STATEMENT\s+ON|BUDGET|BILL|NATIONAL\s+POLICY|CONSENSUS\s+AND)', text, re.I)
    if toc:
        text = text[toc.start():]

    matches = list(DATE_RE.finditer(text))
    speeches = []

    for i, m in enumerate(matches):
        date_str = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

        line_start = text.rfind('\n', 0, m.start()) + 1
        block = text[max(0, line_start - 600):line_start].strip()

        title = []
        for ln in reversed(block.split('\n')):
            ln = ln.strip()
            if not ln: continue
            if re.match(r'^(\d{1,3}|xxx+|i+|v+|x+|NIL|CONTENTS|PREFACE)$', ln, re.I): continue
            if "BACK NOTE" in ln.upper(): break
            title.insert(0, ln)
            if len(title) >= 5: break

        topic = re.sub(r'[*#]', '', " ".join(title)).strip()
        topic = re.sub(r'\s+', ' ', topic).title()
        if not topic or len(topic) < 5:
            topic = "Parliamentary Speech"

        body = text[start:end]
        body = re.split(r'(?i)\bBACK\s+NOTE\b', body)[0]
        body = re.split(r'(?i)\bQUESTIONS\s+AND\s+ANSWERS\b', body)[0]

        if len(body) > 800:
            speeches.append({'date': date_str, 'topic': topic, 'body': body})

    return speeches

def chunk(text, max_w, overlap):
    words = text.split()
    res = []
    step = max_w - overlap
    for i in range(0, len(words), step):
        c = words[i:i+max_w]
        if len(c) < max_w // 4 and i > 0:
            if res:
                res[-1] += " " + " ".join(c)
            break
        res.append(" ".join(c))
    return res

def get_last_id(path):
    if not path.exists() or path.stat().st_size == 0:
        return 0
    with open(path, 'rb') as f:
        try:
            f.seek(-2, os.SEEK_END)
            while f.read(1) != b'\n':
                f.seek(-2, os.SEEK_CUR)
        except OSError:
            f.seek(0)
        last = f.readline().decode()
        if last:
            try:
                return int(json.loads(last)["document_id"].split("_")[-1])
            except:
                pass
    return 0

def main():
    if len(sys.argv) < 3:
        print("usage: prep.py <in_dir> <out_dir>")
        sys.exit(1)

    in_dir = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(exist_ok=True)

    out_jsonl = out_dir / "corpus.jsonl"
    done_txt = out_dir / "done.txt"

    done = set()
    if done_txt.exists():
        done = set(done_txt.read_text().splitlines())

    pdfs = sorted(in_dir.glob("*.pdf"))
    total = len(pdfs)
    if total == 0:
        print("no pdfs found.")
        sys.exit(0)

    doc_id = get_last_id(out_jsonl) + 1

    num_loss = [
        r'\bRs\.\s+(?:to|or)\s+crore\b',
        r'\babout\s+per\s+cent\s+to\s+per\s+cent\b',
        r'\bby\s+hours\b',
        r'\bwelfare of the million people\b'
    ]

    f_out = open(out_jsonl, 'a', encoding='utf-8')
    f_done = open(done_txt, 'a', encoding='utf-8')

    for i, pdf in enumerate(pdfs):
        if pdf.name in done:
            continue

        print(f"[{i+1}/{total}] {pdf.name}")

        text = read_pdf(pdf)
        if not text:
            f_done.write(pdf.name + '\n')
            continue

        text = strip_garbage(text)
        if len(text.split()) < 200:
            f_done.write(pdf.name + '\n')
            continue

        speeches = segment(text)
        if not speeches:
            f_done.write(pdf.name + '\n')
            continue

        for sp in speeches:
            bad = 0
            for pat in num_loss:
                if re.search(pat, sp['body'], re.I):
                    bad = 1
                    break

            if bad:
                doc_id += 1
                continue

            clean = fix_text(sp['body'])
            chunks = chunk(clean, 800, 100)

            for c_idx, c_text in enumerate(chunks):
                row = {
                    "document_id": f"PM_{doc_id:04d}",
                    "chunk_id": f"PM_{doc_id:04d}_{c_idx}",
                    "date": sp['date'],
                    "topic": sp['topic'],
                    "chunk": c_idx,
                    "total": len(chunks),
                    "words": len(c_text.split()),
                    "text": c_text
                }
                f_out.write(json.dumps(row, ensure_ascii=False) + '\n')

            doc_id += 1

        f_done.write(pdf.name + '\n')
        f_done.flush()

    f_out.close()
    f_done.close()
    print("done.")

if __name__ == "__main__":
    main()