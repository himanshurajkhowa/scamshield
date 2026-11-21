"""No training: hand-authored diagnostic probes, not a benchmark or tuning set."""
import json,sys
from pathlib import Path
from unittest.mock import patch
import joblib
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ml.inference import analyze
from ml.rules import analyze_rules
ROOT=Path(__file__).resolve().parents[1]
CASES=[
 ('genuine_credit','genuine','Your account was credited with Rs 1500. Available balance Rs 4200. If you did not expect this transaction, check your bank app. Never share your OTP.'),
 ('genuine_debit','genuine','Your account was debited by INR 450 at a grocery store. Check your bank app if you do not recognise this transaction.'),
 ('genuine_upi','genuine','UPI payment of Rs 250 to the grocery store was successful. Reference 123456789. No action is required.'),
 ('genuine_otp','genuine','Your OTP is 482916 for the login you requested. Never share this code with anyone.'),
 ('genuine_personal','genuine','I will reach the library at four. Please bring the notes.'),
 ('genuine_delivery','genuine','Your parcel has reached the local delivery office. Delivery is expected tomorrow. No payment is required.'),
 ('otp_request','fraud','Share your OTP now to stop account blocking'),
 ('upi_pin','fraud','Aapka cashback ready hai. Receive karne ke liye apna UPI PIN bhejo. Jaldi karo!'),
 ('kyc_threat','fraud','URGENT your account will be blocked. Complete KYC and share your OTP at https://bank-verify.example'),
 ('fake_challan','fraud','Your RTO e-Challan is pending. Pay now at https://echallan.parivahan.gov.in.payments.example')]

def main():
    models={name:joblib.load(ROOT/'ml'/('model_v1.joblib' if name=='v1' else 'model_v2.joblib')) for name in ('v1','v2')}
    output=[]
    for name,label,text in CASES:
        row=dict(case=name,expected_kind=label,rules=analyze_rules(text)[0])
        weight=sum(s['weight'] for s in row['rules'])
        for version,model in models.items():
            with patch('ml.inference.get_model',return_value=model):result=analyze(text)
            row[version]=dict(verdict=result['verdict'],spam_score=result['spam_score'],rule_weight=weight,high_risk_cause=('both' if weight>=3 and result['spam_score']>=.8 else 'rules' if weight>=3 else 'ml' if result['spam_score']>=.8 else 'neither'))
        output.append(row)
    model=models['v2'];vec=model.named_steps['tfidf'].transform([CASES[0][2]]);coef=model.named_steps['classifier'].coef_[0]
    names=model.named_steps['tfidf'].get_feature_names_out();indices=vec.indices;values=vec.data*coef[indices]
    top=sorted(zip(indices,values),key=lambda p:p[1],reverse=True)[:12]
    report=dict(purpose='Hand-authored diagnostic probes only; not held-out accuracy, rule benchmark or a tuning set.',model_version='v2 candidate; active V1 unchanged',cases=output,original_false_positive=dict(rule_signals=output[0]['rules'],cause=output[0]['v2']['high_risk_cause'],top_positive_features=[dict(feature=str(names[i]),logit_contribution=float(v)) for i,v in top]),summary={version:dict(genuine_potential_scam=sum(r['expected_kind']=='genuine' and r[version]['verdict']=='Potential Scam' for r in output),genuine_total=6,fraud_potential_scam=sum(r['expected_kind']=='fraud' and r[version]['verdict']=='Potential Scam' for r in output),fraud_total=4) for version in models})
    (ROOT/'ml/v2_diagnosis.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
    print(json.dumps({'original_false_positive':report['original_false_positive'],'summary':report['summary']},indent=2))
if __name__=='__main__':main()
