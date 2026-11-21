from flask import Flask, jsonify, render_template, request
from ml.inference import analyze
app = Flask(__name__, static_folder='public/static', static_url_path='/static')
app.config['MAX_CONTENT_LENGTH'] = 24000

@app.after_request
def headers(response):
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    if request.path.startswith('/api/'): response.headers['Cache-Control']='no-store'
    return response

@app.get('/')
def index(): return render_template('index.html')

@app.get('/api/health')
def health():
    from ml.inference import get_model
    try:
        model = get_model()
        model.predict_proba(['A routine health check message'])
        if analyze('https://echallan.parivahan.gov.in.evil.example')['verdict'] != 'Potential Scam':
            raise ValueError('URL security smoke failed')
        if analyze('https://echallan.parivahan.gov.in')['verdict'] != 'Needs a Closer Look':
            raise ValueError('Official URL smoke failed')
    except Exception:
        return jsonify(status='model_unavailable', model_ready=False),503
    return jsonify(status='ok', model_ready=True, security_checks=True, security_revision='url-first-2026-11-21'),200

@app.post('/api/analyze')
def detect():
    data = request.get_json(silent=True)
    if not isinstance(data,dict) or not isinstance(data.get('message'),str): return jsonify(error='Send a message as text.'),400
    text = data['message'].strip()
    if len(text)<3 or len(text)>6000: return jsonify(error='Use between 3 and 6,000 characters.'),400
    try: return jsonify(analyze(text))
    except FileNotFoundError: return jsonify(error='The trained model is unavailable. Please finish the offline training step.'),503

@app.errorhandler(413)
def too_large(error): return jsonify(error='Message is too large. Use at most 6,000 characters.'),413

if __name__=='__main__': app.run(host='127.0.0.1',port=5000,debug=False)
