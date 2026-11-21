"""Offline training: python training/train.py [--data path/to/SMSSpamCollection]."""
import argparse, hashlib, json, re, unicodedata, urllib.request, zipfile, io
from pathlib import Path
import joblib
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://archive.ics.uci.edu/static/public/228/sms+spam+collection.zip'

def clean(text):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', text)).strip()

def prepare(raw):
    records, conflicts = {}, set()
    for line in raw.splitlines():
        if '\t' not in line: continue
        label, text = line.split('\t', 1)
        text = clean(text)
        if label not in ('ham', 'spam') or not text: continue
        key = text.casefold()
        if key in records and records[key][1] != label: conflicts.add(key)
        records[key] = (text, label)
    return [v for k,v in records.items() if k not in conflicts], len(conflicts)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path)
    args = parser.parse_args()
    if args.data:
        payload = args.data.read_bytes()
    else:
        with urllib.request.urlopen(URL, timeout=30) as response:
            archive = response.read()
        payload = zipfile.ZipFile(io.BytesIO(archive)).read('SMSSpamCollection')
    records, conflicts = prepare(payload.decode('utf-8'))
    if len(records) < 1000: raise ValueError('Incomplete corpus: expected at least 1000 unique messages')
    texts, labels = zip(*records)
    X_train, X_test, y_train, y_test = train_test_split(texts, labels, test_size=.2, random_state=42, stratify=labels)
    pipeline = Pipeline([('tfidf', TfidfVectorizer(ngram_range=(1,2), max_features=18000, sublinear_tf=True)), ('classifier', LogisticRegression(C=4, class_weight='balanced', max_iter=1000, random_state=42))])
    pipeline.fit(X_train, y_train)
    pred = pipeline.predict(X_test)
    path = ROOT / 'ml/model.joblib'
    joblib.dump(pipeline, path, compress=3)
    report = dict(source='UCI SMS Spam Collection', source_url=URL, license='CC BY 4.0', indian_training_data=False, raw_sha256=hashlib.sha256(payload).hexdigest(), unique_messages=len(records), conflicting_duplicates_removed=conflicts, train_size=len(X_train), test_size=len(X_test), seed=42, accuracy=accuracy_score(y_test,pred), precision=precision_score(y_test,pred,pos_label='spam'), recall=recall_score(y_test,pred,pos_label='spam'), f1=f1_score(y_test,pred,pos_label='spam'), confusion_matrix_labels=['ham','spam'], confusion_matrix=confusion_matrix(y_test,pred,labels=['ham','spam']).tolist(), model_bytes=path.stat().st_size)
    (ROOT/'ml/metrics.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
if __name__ == '__main__': main()
