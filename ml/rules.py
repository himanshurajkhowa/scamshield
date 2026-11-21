"""Explainable text heuristics. URL parsing is offline: no DNS or HTTP requests."""
import re

def analyze_rules(text, url_result=None):
    t = text.casefold()
    signals = []
    def add(code, title, detail, weight):
        signals.append(dict(code=code, title=title, detail=detail, weight=weight))
    # Ignore explicit safety advice before looking for credential requests.
    clauses = re.split(r'[.!?;\n]+', t)
    credential = any(re.search(r'\b(share|send|tell|provide|enter|batao|bhejo|do)\b.{0,45}\b(otp|upi\s*pin|password)\b|\b(otp|upi\s*pin|password)\b.{0,25}\b(bhejo|batao)\b', c) and not re.search(r'\b(never|not|don.t|do not|mat|nahi)\b', c) for c in clauses)
    if credential: add('credentials','Request for a secret','The text asks for an OTP, UPI PIN or password. Never share these with another person.',3)
    if re.search(r'\b(kyc|pan|aadhaar|aadhar)\b',t) and re.search(r'block|suspend|expire|deactivat|band ho',t):
        add('kyc','KYC or account-blocking pressure','Identity verification is paired with a threat of losing access.',2)
    if re.search(r'\b(urgent|immediately|last warning|within \d+ (?:hours|minutes)|arrest|legal action|abhi|jaldi)\b',t):
        add('pressure','Pressure to act quickly','Urgency can discourage you from checking the sender.',1)
    if re.search(r'\b(won|lottery|reward|cashback|refund|prize)\b',t) and re.search(r'claim|pay|fee|click|send|deposit',t):
        add('reward','Reward or refund with a catch','A reward or refund is paired with an action or payment request.',2)
    if re.search(r'deliver|parcel|courier|shipment',t) and re.search(r'pay|fee|charge|payment',t):
        add('delivery','Delivery payment request','Check any delivery charge through the courier’s official app or website.',1)
    from .urls import inspect_urls
    if url_result is None:
        url_result = inspect_urls(text)
    signals.extend(url_result['signals'])
    signals = list({s['code']:s for s in signals}.values())
    return signals, url_result['hosts']
