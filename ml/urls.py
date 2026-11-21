"""Offline URL inspection. No network operations or destination reputation claims."""
import ipaddress
import re
import unicodedata
from urllib.parse import urlsplit, unquote

# Fixed reference hosts, not a certificate, ownership or destination-content check.
# eChallan: CERT-In CICA-2026-3492 and the MoRTH NextGen portal (21 Nov 2026).
CHALLAN_HOSTS = frozenset(('echallan.parivahan.gov.in','echallan.parivahan.nic.in'))
REFERENCE_HOSTS = frozenset((*CHALLAN_HOSTS,'parivahan.gov.in','sbi.co.in','hdfcbank.com','icicibank.com','rbi.org.in','npci.org.in','uidai.gov.in','indiapost.gov.in'))
TOKENS = ('parivahan','echallan','challan','hdfcbank','icicibank','indiapost','uidai','npci','sbi','rbi')
SCHEME = r'(?:[a-z][a-z0-9+.-]*://|(?:javascript|data|file|vbscript|intent|market):|//)'
BARE = r'(?:www\.)?(?:[\w\-]+\.)+(?:[a-z\u0080-\uffff]{2,63})(?::\d+)?(?:[/\?#][^\s<>"\x27]*)?|(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?(?:/[^\s<>"\x27]*)?'
URL_RE = re.compile(r'(?<![\w@])(?:'+SCHEME+r'[^\s<>"\x27]+|'+BARE+r')',re.I)
CLAIM_RE = re.compile(r'\b(?:e[\s-]?challan|challan|parivahan|rto|traffic\s+(?:police|fine)|morth)\b',re.I)
CONFUSABLES = str.maketrans({'а':'a','е':'e','о':'o','р':'p','с':'c','х':'x','і':'i','ј':'j','ӏ':'l','ν':'v','ɑ':'a','0':'o','1':'i'})

def extract_urls(text):
    found=[]
    for match in URL_RE.finditer(text):
        value=match.group().rstrip('.,;!?')
        while value.endswith(')') and value.count(')')>value.count('('):value=value[:-1]
        found.append((value,match.start(),match.start()+len(value)))
    return found

def is_standalone_url(text):
    stripped=text.strip()
    found=extract_urls(stripped)
    return len(found)==1 and found[0][1]==0 and found[0][2]==len(stripped.rstrip('.,;!?'))

def near(a,b):
    # Bounded edit distance only for longer names; avoid matching short words to SBI/RBI.
    if len(b)<5 or abs(len(a)-len(b))>1:return False
    previous=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        current=[i]
        for j,y in enumerate(b,1):current.append(min(current[-1]+1,previous[j]+1,previous[j-1]+(x!=y)))
        previous=current
    return 0<previous[-1]<=1

def inspect_urls(text):
    findings={};hosts=[];links=[]
    def add(code,title,detail,weight):findings.setdefault(code,dict(code=code,title=title,detail=detail,weight=weight))
    matches=extract_urls(text)
    if len(matches)>20:add('url_limit','More links than checked','Only the first 20 links were inspected. Check the remaining links independently.',1)
    for raw,_,_ in matches[:20]:
        item=dict(host=None,scheme=None,reference_match=False,challan_reference=False)
        try:
            normalized=unicodedata.normalize('NFKC',raw)
            if '\\' in raw or any(ord(c)<32 for c in raw):
                add('url_ambiguous','Ambiguous link syntax','Backslashes or control characters can make browsers interpret a link differently. Do not use this link.',3)
            parsed=urlsplit(normalized if re.match(r'^[a-z][a-z0-9+.-]*:',normalized,re.I) else ('https:'+normalized if normalized.startswith('//') else 'https://'+normalized))
            scheme=parsed.scheme.casefold();item['scheme']=scheme
            if scheme not in ('http','https'):
                add('url_scheme','Link uses a non-web scheme',f'The {scheme} scheme can launch an app, access a file or run content. It was not executed.',3)
            host=(parsed.hostname or '').rstrip('.').casefold()
            if not host:
                if scheme in ('http','https'):raise ValueError('missing hostname')
                links.append(item);continue
            if '%' in host or any(c.isspace() for c in host):raise ValueError('encoded or invalid hostname')
            ascii_host=host.encode('idna').decode('ascii')
            # Accessing port validates malformed/non-numeric/out-of-range port syntax.
            port=parsed.port
            try:
                ipaddress.ip_address(host);is_ip=True
            except ValueError:
                is_ip=False
                if not all(re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?',part) for part in ascii_host.split('.')):raise ValueError('invalid hostname')
            hosts.append(ascii_host);item['host']=ascii_host
            # Exact reference match only. A subdomain is not automatically approved.
            item['reference_match']=ascii_host in REFERENCE_HOSTS
            item['challan_reference']=ascii_host in CHALLAN_HOSTS
            if is_ip:add('url_ip','Link points to an IP address',f'The actual host is {ascii_host}, not a named service. Verify independently before using it.',2)
            if parsed.username is not None or parsed.password is not None:
                add('url_userinfo','Displayed service may hide the real host',f'Text before @ is not the destination. The actual host is {ascii_host}.',3)
            if scheme=='http':add('url_http','Link is not encrypted','This link uses HTTP. Verify the service independently before entering information.',1)
            if port not in (None,80,443):add('url_port','Link uses an unusual port',f'The destination uses port {port}; verify independently.',1)
            if any(part.startswith('xn--') for part in ascii_host.split('.')):
                add('url_idn','Internationalized hostname','The link contains an encoded international hostname. Check its spelling carefully; this alone does not prove fraud.',1)
            skeleton=host.translate(CONFUSABLES)
            labels=re.split(r'[.\-]',skeleton)
            if not item['reference_match']:
                deceptive=any(d+'.' in ascii_host or ascii_host.endswith('.'+d) for d in REFERENCE_HOSTS)
                if deceptive:
                    add('url_deceptive','Official-looking text is not the reference host',f'The actual host is {ascii_host}. An official name embedded in another host does not make it official.',3)
                named=any(token in skeleton for token in TOKENS if len(token)>=5) or any(x in ('sbi','rbi','rto') for x in labels)
                lookalike=any(near(label,token) for label in labels for token in TOKENS)
                if named or lookalike:
                    add('impersonation','Service name in an unverified hostname',f'The actual host is {ascii_host}, outside the small reference list. It contains a familiar service name or close spelling; confirm through the official service.',1 if ascii_host.endswith(('.gov.in','.nic.in')) else 3)
                if re.search(r'(?:^|[.\-])gov(?:[.\-]|$)',ascii_host) and not ascii_host.endswith(('.gov.in','.nic.in')):
                    add('url_government','Government-looking hostname',f'The actual host {ascii_host} uses government-looking labels outside .gov.in or .nic.in.',3)
                if ascii_host in ('bit.ly','tinyurl.com','t.co'):
                    add('url_shortener','Short link hides the destination','The final destination is not visible. The short link was not followed.',1)
                if ascii_host.endswith(('.xyz','.top','.click')):
                    add('url','Link needs independent verification','This domain suffix warrants another check. A suffix alone does not prove fraud.',1)
            decoded_path=unquote(parsed.path).casefold()
            if decoded_path.endswith('.apk'):
                add('url_apk','Link offers an Android installer','An APK from a message can install software with sensitive permissions. This file was not downloaded.',3)
            links.append(item)
        except (ValueError,UnicodeError):
            add('url','Malformed link','The hostname or URL syntax could not be parsed safely. Do not rely on its displayed name.',2)
            links.append(item)
    # Match the claimed service to actual hosts, including when a fake host has no service name.
    challan_claim=bool(CLAIM_RE.search(text))
    nonofficial=[x for x in links if not x['challan_reference']]
    payment=bool(re.search(r'\b(?:pay|payment|fine|penalty|dues|pending|settle|challan)\b',text,re.I))
    if challan_claim and nonofficial:
        add('challan_mismatch','e-Challan service and link do not match','This message mentions RTO/e-Challan but links outside the two checked e-Challan hostnames. Independently use echallan.parivahan.gov.in or your verified state traffic-police portal; this list does not cover every legitimate state service.',3 if payment and any(not (x.get('host') or '').endswith(('.gov.in','.nic.in')) for x in nonofficial) else 1)
    return dict(signals=list(findings.values()),hosts=list(dict.fromkeys(hosts)),links=links,standalone=is_standalone_url(text))
