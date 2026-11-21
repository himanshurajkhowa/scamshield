import socket
import unittest
from unittest.mock import patch
from ml.urls import inspect_urls
from ml.inference import analyze
from app import app

class URLSecurityTests(unittest.TestCase):
    def test_fake_challan(self):
        for text in ('Your RTO challan is pending. Pay at https://challan-pay.example',
                     'e-Challan payment due: https://payments.example/pay',
                     'https://echallanparivahan.example/pay',
                     'https://echallan.parivahan.gov.in.evil.example/pay',
                     'https://echallan-parivahan-gov.in/pay'):
            with self.subTest(text=text):
                r=analyze(text);self.assertEqual(r['verdict'],'Potential Scam');self.assertTrue(r['signals'])
    def test_reference_host_boundaries(self):
        for url in ('https://echallan.parivahan.gov.in/','https://ECHALLAN.PARIVAHAN.GOV.IN./index/challan-status','https://echallan.parivahan.nic.in/'):
            with self.subTest(url=url):
                info=inspect_urls(url);self.assertTrue(info['links'][0]['challan_reference']);self.assertFalse(info['signals'])
                result=analyze(url);self.assertEqual(result['verdict'],'Needs a Closer Look');self.assertEqual(result['model_assessment'],'Not used for URL-only verdict')
    def test_url_only_ignores_model_verdict_score(self):
        from ml.inference import get_model
        model=get_model()
        with patch.object(model,'predict_proba',return_value=__import__('numpy').array([[.001,.999]])):
            self.assertEqual(analyze('https://unknown.example/')['verdict'],'Needs a Closer Look')
    def test_deceptive_userinfo_and_subdomain(self):
        for url in ('https://echallan.parivahan.gov.in@evil.example/pay',
                    'https://sbi.co.in.evil.example',
                    'https://login.echallan.parivahan.gov.in'):
            with self.subTest(url=url):self.assertEqual(analyze(url)['verdict'],'Potential Scam')
        self.assertEqual(inspect_urls('https://echallan.parivahan.gov.in@evil.example')['hosts'],['evil.example'])
    def test_lookalike_domains(self):
        for url in ('https://parivahann.example','https://hdfcbnk.example','https://echallan.parivahаn.example'):
            with self.subTest(url=url):self.assertEqual(analyze(url)['verdict'],'Potential Scam')
    def test_schemes(self):
        for url in ('javascript:alert(1)','data:text/html,test','file:///etc/passwd','ftp://files.example/test'):
            with self.subTest(url=url):self.assertEqual(analyze(url)['verdict'],'Potential Scam')
    def test_ip_links(self):
        for url in ('http://192.0.2.10/pay','https://[2001:db8::1]/pay'):
            with self.subTest(url=url):
                result=inspect_urls(url);self.assertIn('url_ip',{s['code'] for s in result['signals']})
    def test_unknown_domain_not_proof(self):
        result=analyze('https://ordinary.example/path');self.assertEqual(result['verdict'],'Needs a Closer Look');self.assertFalse(result['signals'])
    def test_government_impersonation(self):
        result=analyze('Government payment portal https://gov.in.payments.example')
        self.assertEqual(result['verdict'],'Potential Scam')
        result=analyze('Check your challan on https://traffic.state.gov.in')
        self.assertEqual(result['verdict'],'Needs a Closer Look')
    def test_apk(self):
        result=analyze('Download your RTO receipt https://download.example/receipt%2Eapk')
        self.assertEqual(result['verdict'],'Potential Scam');self.assertIn('url_apk',{s['code'] for s in result['signals']})
    def test_no_network(self):
        with patch('socket.getaddrinfo',side_effect=AssertionError('DNS attempted')),patch('urllib.request.urlopen',side_effect=AssertionError('HTTP attempted')),patch('socket.socket',side_effect=AssertionError('Socket attempted')):
            self.assertEqual(analyze('RTO challan pay https://echallan.parivahan.gov.in.evil.example')['verdict'],'Potential Scam')
    def test_malformed_and_ambiguous(self):
        for url in ('https://[broken','https://example.com:invalid','https://example.com\\@other.example','https://gov%2ein.example'):
            with self.subTest(url=url):self.assertTrue(inspect_urls(url)['signals'])
    def test_api_shape_preserved(self):
        result=app.test_client().post('/api/analyze',json={'message':'Pay e-Challan at https://payments.example'})
        self.assertEqual(result.status_code,200)
        for key in ('verdict','state','explanation','spam_score','signals','domains','recommendations'):self.assertIn(key,result.json)
        self.assertEqual(result.json['analysis_type'],'message')
    def test_ordinary_and_genuine(self):
        for text in ('I will reach the library at four. Bring your notes.',
                     'Your account was credited with Rs 1500. Available balance Rs 4200. If you did not expect this transaction, check your bank app. Never share your OTP.'):
            with self.subTest(text=text):self.assertEqual(analyze(text)['verdict'],'No Strong Scam Indicators')
