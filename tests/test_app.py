import unittest
from unittest.mock import patch
from app import app
from ml.inference import analyze, get_model
from ml.rules import analyze_rules
from training.train import prepare

class ScamShieldTests(unittest.TestCase):
    def setUp(self): self.client=app.test_client()
    def test_home(self):
        r=self.client.get('/')
        self.assertEqual(r.status_code,200)
        self.assertIn(b'That message feels',r.data)
        self.assertIn(b'id="scanner" class="scanner" hidden',r.data)
        self.assertIn('frame-ancestors',r.headers['Content-Security-Policy'])
    def test_validation(self):
        for payload in ({},{'message':None},{'message':4},{'message':'  '},{'message':'a'*6001},[]):
            self.assertEqual(self.client.post('/api/analyze',json=payload).status_code,400)
        self.assertEqual(self.client.post('/api/analyze',data='x',content_type='text/plain').status_code,400)
    def test_body_limit(self):
        self.assertEqual(self.client.post('/api/analyze',json={'message':'x'*25000}).status_code,413)
    def test_rules(self):
        signals,_=analyze_rules('Urgent SBI KYC account blocked. Share your OTP at https://sbi-verify.example')
        self.assertTrue({'credentials','kyc','pressure','impersonation'} <= {s['code'] for s in signals})
    def test_safety_advice(self):
        for text in ('Never share your OTP.','Do not share your UPI PIN.','OTP mat bhejo.'):
            signals,_=analyze_rules(text)
            self.assertNotIn('credentials',{s['code'] for s in signals})
    def test_url_parsing(self):
        with patch('socket.getaddrinfo',side_effect=AssertionError('No DNS allowed')):
            signals,hosts=analyze_rules('Check https://user@127.0.0.1/pay and https://[malformed')
        self.assertIn('127.0.0.1',hosts)
        self.assertIn('url',{s['code'] for s in signals})
    def test_deduplication(self):
        records,conflicts=prepare('ham\t Hello world\nham\thello   world\nspam\tWin prize\nham\tConflict\nspam\tconflict\nbad\tno')
        self.assertEqual(len(records),2)
        self.assertEqual(conflicts,1)
    def test_missing_model(self):
        with patch('ml.inference.get_model',side_effect=FileNotFoundError):
            self.assertEqual(self.client.post('/api/analyze',json={'message':'Hello there friend'}).status_code,503)
    def test_actual_inference(self):
        r=self.client.post('/api/analyze',json={'message':'Share your OTP now to stop your account being blocked'})
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json['verdict'],'Potential Scam')
        self.assertTrue(0<=r.json['spam_score']<=1)
        self.assertEqual(r.headers['Cache-Control'],'no-store')
    def test_ordinary_message(self):
        self.assertEqual(analyze('Hey, I will reach the library at 4 pm. Please bring the notes from yesterday.')['verdict'],'No Strong Scam Indicators')
    def test_transactional_message(self):
        text='Your account was credited with Rs 1500. Available balance Rs 4200. If you did not expect this transaction, check your bank app. Never share your OTP.'
        self.assertEqual(analyze(text)['verdict'],'No Strong Scam Indicators')
    def test_uncertainty(self):
        self.assertEqual(analyze('https://hello.example')['verdict'],'Needs a Closer Look')
    def test_model_cached(self): self.assertIs(get_model(),get_model())
    def test_health(self): self.assertTrue(self.client.get('/api/health').json['model_ready'])

if __name__=='__main__':unittest.main()
