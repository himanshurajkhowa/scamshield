"""Bounded V2 candidate. Never overwrites the active or V1 model.
Run from project root: .venv/bin/python training/train_v2.py --enron path/to/enron_spam_data.zip
"""
import argparse, csv, hashlib, html, io, json, re, time, unicodedata, zipfile
from collections import Counter, defaultdict
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score,precision_score,recall_score,f1_score,confusion_matrix
from training.train import prepare
ROOT=Path(__file__).resolve().parents[1]

def normalize(text):
    return re.sub(r'\s+',' ',unicodedata.normalize('NFKC',html.unescape(text))).strip()[:6000]

def group_key(text):
    text=normalize(text).casefold()
    text=re.sub(r'https?://\S+|www\.\S+',' URL ',text)
    text=re.sub(r'\b\S+@\S+\b',' EMAIL ',text)
    text=re.sub(r'\d+',' NUMBER ',text)
    text=re.sub(r'[^\w\s]',' ',text)
    return re.sub(r'\s+',' ',text).strip()

def digest(value):return hashlib.sha256(value.encode()).hexdigest()
def scores(y,p):
    return dict(n=len(y),accuracy=float(accuracy_score(y,p)),precision=float(precision_score(y,p,pos_label='spam',zero_division=0)),recall=float(recall_score(y,p,pos_label='spam',zero_division=0)),f1=float(f1_score(y,p,pos_label='spam',zero_division=0)),confusion_matrix=confusion_matrix(y,p,labels=['ham','spam']).tolist())

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--enron',type=Path,required=True);args=parser.parse_args()
    start=time.perf_counter();data=ROOT/'training/data';provenance=[];rows=[]
    raw=(data/'SMSSpamCollection').read_bytes();uci,_=prepare(raw.decode())
    _,old_test=train_test_split(list(range(len(uci))),test_size=.2,random_state=42,stratify=[r[1] for r in uci])
    # Original V1 holdout membership is immutable. Related templates are also held out.
    old_holdout={normalize(uci[i][0]).casefold() for i in old_test}
    for text,label in uci:rows.append(dict(text=normalize(text),label=label,source='uci',old_test=normalize(text).casefold() in old_holdout))
    provenance.append(dict(source='uci',url='https://archive.ics.uci.edu/dataset/228/sms+spam+collection',license='CC BY 4.0',raw_sha256=hashlib.sha256(raw).hexdigest(),raw_records=len(uci)))
    raw=(data/'india_sms.csv').read_bytes();indian=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
    for r in indian:
        if r['Label'].strip() in ('spam','ham') and r['Msg'].strip():rows.append(dict(text=normalize(r['Msg']),label=r['Label'].strip(),source='india_sms',old_test=False))
    provenance.append(dict(source='india_sms',url='https://github.com/junioralive/india-spam-sms-classification',license='MIT',git_blob='2f8552223ceafc22ce634a659a5f947ad44e4d88',raw_sha256=hashlib.sha256(raw).hexdigest(),raw_records=len(indian)))
    payload=args.enron.read_bytes();csv.field_size_limit(10_000_000)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        name=next(n for n in archive.namelist() if n.endswith('.csv'))
        with io.TextIOWrapper(archive.open(name),encoding='utf-8-sig',errors='replace') as f:emails=list(csv.DictReader(f))
    selected=[]
    # Deterministic bounded sample before any evaluation; 3000 per class maximum.
    for label in ('ham','spam'):
        eligible=[r for r in emails if r.get('Spam/Ham','').strip()==label]
        eligible.sort(key=lambda r:digest(str(r.get('Subject',''))+'\n'+str(r.get('Message',''))))
        selected.extend(eligible[:3000])
    for r in selected:
        body=str(r.get('Message',''))
        body=re.split(r'(?im)^\s*(?:-+\s*original message\s*-+|from:|forwarded by)',body)[0]
        body='\n'.join(line for line in body.splitlines() if not line.lstrip().startswith('>'))
        body=re.sub(r'(?is)<(?:script|style)\b[^>]*>.*?</(?:script|style)>',' ',body)
        body=re.sub(r'<[^>]+>',' ',body)
        text=normalize(str(r.get('Subject',''))+'\n'+body)
        if len(text)>10:rows.append(dict(text=text,label=r['Spam/Ham'].strip(),source='enron',old_test=False))
    provenance.append(dict(source='enron',url='https://github.com/MWiechmann/enron_spam_data',license='GPL-3.0 repository; original email rights remain with senders',raw_sha256=hashlib.sha256(payload).hexdigest(),raw_records=len(emails),bounded_sample=len(selected)))
    # Global exact deduplication, retaining every source and V1 test provenance.
    merged={};conflicts=set()
    for r in rows:
        key=r['text'].casefold()
        if key in merged:
            prev=merged[key]
            if prev['label']!=r['label']:conflicts.add(key)
            prev['old_test'] |= r['old_test'];prev['sources'].add(r['source'])
        else:merged[key]={**r,'sources':{r['source']}}
    clean=[r for k,r in merged.items() if k not in conflicts]
    # Group template variants globally (including different source labels).
    groups=defaultdict(list)
    for r in clean:groups[group_key(r['text'])].append(r)
    train=[];test=[];excluded=[]
    for key,items in groups.items():
        if len({r['label'] for r in items})>1:
            excluded.extend(items);continue
        has_old_test=any(r['old_test'] for r in items)
        has_uci=any('uci' in r['sources'] for r in items)
        is_test=has_old_test or (not has_uci and int(digest('42:'+key)[:8],16)%5==0)
        for r in items:
            r['group']=digest(key);(test if is_test else train).append(r)
    assert not ({r['text'].casefold() for r in train}&{r['text'].casefold() for r in test})
    assert not ({r['group'] for r in train}&{r['group'] for r in test})
    assert not any(r['old_test'] for r in train)
    # Comparison excludes new-source messages V1 saw under UCI provenance.
    new_test=[r for r in test if 'uci' not in r['sources']]
    model=Pipeline([('tfidf',FeatureUnion([
        ('word',TfidfVectorizer(ngram_range=(1,2),max_features=18000,min_df=2,sublinear_tf=True,dtype=np.float32,token_pattern=r'(?u)\b\w+\b')),
        ('char',TfidfVectorizer(analyzer='char_wb',ngram_range=(3,5),max_features=30000,min_df=3,sublinear_tf=True,dtype=np.float32))
    ])),('classifier',LogisticRegression(C=4,solver='liblinear',max_iter=500,random_state=42))])
    counts=Counter((r['source'],r['label']) for r in train)
    weights=np.array([1/np.sqrt(counts[(r['source'],r['label'])]) for r in train]);weights/=weights.mean()
    model.fit([r['text'] for r in train],[r['label'] for r in train],classifier__sample_weight=weights)
    v1=joblib.load(ROOT/'ml/model_v1.joblib')
    comparison={}
    for name,subset in [('all',test),('uci_original_holdout',[r for r in test if r['old_test']]),('uci_grouped',[r for r in test if 'uci' in r['sources']]),('india_sms_novel',[r for r in new_test if 'india_sms' in r['sources']]),('enron_novel',[r for r in new_test if 'enron' in r['sources']])]:
        if not subset:continue
        X=[r['text'] for r in subset];y=[r['label'] for r in subset]
        comparison[name]={'v1':scores(y,v1.predict(X)),'v2':scores(y,model.predict(X))}
    candidate=ROOT/'ml/model_v2.joblib';joblib.dump(model,candidate,compress=3)
    report=dict(version='v2-candidate',active_version='v1',status='NOT_PROMOTED_PENDING_GATES',provenance=provenance,excluded_sources={'iiit_delhi':'Mirror has no explicit data reuse license; original requester requires access request.','spamassassin':'No explicit redistribution license; sender copyrights retained. Enron chosen instead.','hindi_mt':'Readily found dataset is poor machine translation of UCI, not original Hindi; ambiguous GPL version and no quality validation within timebox.'},raw_loaded=len(rows),unique_retained=len(train)+len(test),exact_conflicts=len(conflicts),template_conflict_records=len(excluded),train_records=len(train),test_records=len(test),train_by_source=dict(Counter(r['source'] for r in train)),test_by_source=dict(Counter(r['source'] for r in test)),comparison=comparison,model_bytes=candidate.stat().st_size,fit_seconds=round(time.perf_counter()-start,2),seed=42,leakage_checks={'exact_overlap':0,'template_group_overlap':0,'v1_test_in_training':0},limitations=['No IIIT or Hindi corpus included. Indian source is not a dedicated Hinglish benchmark.','Promotional spam labels are not fraud labels. Historic Enron is not modern email coverage.','Template normalization prevents exact/URL/number variants crossing splits; paraphrases and complex thread overlap may remain.','Per-source primary attribution uses UCI first; new-source comparison excludes overlap with any UCI record.'])
    (ROOT/'ml/metrics_v2.json').write_text(json.dumps(report,indent=2))
    # Only hashes and labels in tracked receipt. Raw messages stay ignored.
    receipt=[dict(sha256=digest(r['text'].casefold()),group=r['group'],source=r['source'],label=r['label'],split=split,old_test=r['old_test']) for split,rs in [('train',train),('test',test)] for r in rs]
    (data/'v2_split_receipt.json').write_text(json.dumps(receipt))
    (data/'v2_evaluation.json').write_text(json.dumps(test,default=lambda x:sorted(x)))
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
