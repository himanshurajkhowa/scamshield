"""Compare saved V1/V2 without retraining. Reads ignored local evaluation rows."""
import json, sys, hashlib
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import joblib
from sklearn.model_selection import train_test_split
from training.train import prepare
from training.train_v2 import scores
from app import app
ROOT=Path(__file__).resolve().parents[1]

def main():
    report=json.loads((ROOT/'ml/metrics_v2.json').read_text())
    rows=json.loads((ROOT/'training/data/v2_evaluation.json').read_text())
    v1=joblib.load(ROOT/'ml/model_v1.joblib');v2=joblib.load(ROOT/'ml/model_v2.joblib')
    uci,_=prepare((ROOT/'training/data/SMSSpamCollection').read_text())
    _,idx=train_test_split(list(range(len(uci))),test_size=.2,random_state=42,stratify=[r[1] for r in uci])
    comparison={}
    # Exactly the original V1 input texts, not HTML-unescaped V2 preparation.
    original=[uci[i] for i in idx]
    for name,pairs in [('uci_original_holdout',original),('all_common_holdout',original+[(r['text'],r['label']) for r in rows if 'uci' not in r['sources']]),('india_sms_novel',[(r['text'],r['label']) for r in rows if 'uci' not in r['sources'] and 'india_sms' in r['sources']]),('enron_novel',[(r['text'],r['label']) for r in rows if 'uci' not in r['sources'] and 'enron' in r['sources']])]:
        X=[p[0] for p in pairs];y=[p[1] for p in pairs]
        comparison[name]={version:scores(y,model.predict(X)) for version,model in [('v1',v1),('v2',v2)]}
    # Candidate's full grouped test includes 24 UCI training rows withheld only from V2.
    # These are deliberately excluded from all_common_holdout for a fair V1 comparison.
    comparison['v2_all_grouped']=scores([r['label'] for r in rows],v2.predict([r['text'] for r in rows]))
    smoke=[]
    cases=[('otp_request','Share your OTP now to stop account blocking','Potential Scam'),('ordinary','Hey, I will reach the library at 4 pm. Please bring the notes from yesterday.','No Strong Scam Indicators'),('genuine_transaction','Your account was credited with Rs 1500. Available balance Rs 4200. If you did not expect this transaction, check your bank app. Never share your OTP.','No Strong Scam Indicators')]
    with patch('ml.inference.get_model',return_value=v2):
        for name,text,expected in cases:
            response=app.test_client().post('/api/analyze',json={'message':text})
            smoke.append(dict(case=name,http_status=response.status_code,expected=expected,actual=response.json.get('verdict'),spam_score=response.json.get('spam_score'),passed=response.status_code==200 and response.json.get('verdict')==expected))
    report.update(comparison=comparison,smoke_tests=smoke,status='REJECTED_SMOKE_REGRESSION',active_version='v1',promotion_reason='V2 classifies the existing genuine transactional example as Potential Scam (score 0.9269); V1 returns No Strong Scam Indicators. Failed smoke gate; no deployment or promotion attempted.',model_sha256=hashlib.sha256((ROOT/'ml/model_v2.joblib').read_bytes()).hexdigest(),active_v1_unchanged=hashlib.sha256((ROOT/'ml/model.joblib').read_bytes()).digest()==hashlib.sha256((ROOT/'ml/model_v1.joblib').read_bytes()).digest())
    (ROOT/'ml/metrics_v2.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(dict(status=report['status'],comparison=comparison,smoke_tests=smoke,active_v1_unchanged=report['active_v1_unchanged']),indent=2))
if __name__=='__main__':main()
