from functools import lru_cache
from pathlib import Path
import joblib
from .rules import analyze_rules
from .urls import inspect_urls

@lru_cache(maxsize=1)
def get_model():
    return joblib.load(Path(__file__).with_name('model.joblib'))

def analyze(text):
    url_result = inspect_urls(text)
    model = get_model()
    score = float(model.predict_proba([text])[0][list(model.classes_).index('spam')])
    vector = model.named_steps['tfidf'].transform([text])
    signals, hosts = analyze_rules(text, url_result=url_result)
    weight = sum(s['weight'] for s in signals)
    uncertain = vector.nnz == 0 or len(text.split()) < 4
    # Standalone URL verdicts use URL evidence, never the SMS classifier score.
    verdict_score = 0.0 if url_result['standalone'] else score
    if verdict_score >= .8 or weight >= 3:
        verdict, state = 'Potential Scam', 'danger'
        explanation = 'This message contains strong warning signs. Pause before replying, paying or sharing information.'
    elif verdict_score >= .3 or weight > 0 or uncertain or url_result['standalone']:
        verdict, state = 'Needs a Closer Look', 'caution'
        explanation = 'There is not enough clear evidence to trust this message. Check the sender through an independent channel.'
    else:
        verdict, state = 'No Strong Scam Indicators', 'clear'
        explanation = 'The checks found no strong warning signs in this text. This does not establish that the sender or links are safe.'
    assessment = 'Spam-like' if score >= .8 else ('Mixed or uncertain' if score >= .3 or uncertain else 'Mostly non-spam-like')
    if url_result['standalone']:
        assessment = 'Not used for URL-only verdict'
        if state != 'danger':
            explanation = 'A URL alone cannot establish safety. The hostname was inspected without opening the link; verify the service independently.'
    return dict(analysis_type='url' if url_result['standalone'] else 'message',url_analysis=url_result['links'],verdict=verdict,state=state,explanation=explanation,model_assessment=assessment,spam_score=round(score,4),score_note='Uncalibrated spam classification score; not a probability of fraud.',signals=signals,domains=hosts,recommendations=['Verify the sender using an official app or a contact you already know.','Never share an OTP, UPI PIN or password.','Do not pay or open a link just because a message pressures you.'])
