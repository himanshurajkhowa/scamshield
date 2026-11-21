'use strict';
const $ = id => document.getElementById(id);
const examples = [
 ['Fake Bank / KYC Alert','URGENT: Your SBI account will be blocked within 2 hours. Update KYC at https://sbi-verify.example and share your OTP to avoid suspension.'],
 ['UPI Payment Scam','Aapka cashback ready hai. Receive karne ke liye apna UPI PIN bhejo. Jaldi karo, reward claim abhi!'],
 ['Suspicious Delivery Link','Your parcel could not be delivered. Pay a redelivery fee of Rs 5 at https://delivery-pay.example to release your parcel.'],
 ['Genuine Transactional Message','Your account was credited with Rs 1500. Available balance Rs 4200. If you did not expect this transaction, check your bank app. Never share your OTP.'],
 ['Ordinary Personal Message','Hey, I will reach the library at 4 pm. Please bring the notes from yesterday.'],
 ['Ambiguous Message','Hi, please check the details I sent earlier and confirm when you can.']
];
let request;
let transitioning = false;
const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;
function count(){ $('counter').textContent = `${$('message').value.length.toLocaleString()} / 6,000`; }
async function scanner(open){
 if(transitioning)return;
 const swap=()=>{$('landing').hidden=open;$('scanner').hidden=!open;window.scrollTo(0,0);};
 if(!open || reducedMotion() || !Element.prototype.animate){swap();(open?$('message'):$('start')).focus({preventScroll:true});return;}
 transitioning=true;
 const button=$('start'), rect=button.getBoundingClientRect(), veil=$('scanner-reveal');
 const x=rect.left+rect.width/2,y=rect.top+rect.height/2;
 const radius=Math.hypot(Math.max(x,innerWidth-x),Math.max(y,innerHeight-y));
 button.setAttribute('aria-busy','true');veil.hidden=false;
 try{
  await veil.animate([{clipPath:`circle(${rect.height/2}px at ${x}px ${y}px)`},{clipPath:`circle(${radius}px at ${x}px ${y}px)`}],{duration:460,easing:'cubic-bezier(.16,1,.3,1)',fill:'forwards'}).finished;
  swap();
  await veil.animate([{backgroundColor:'var(--terracotta)',opacity:1},{backgroundColor:'var(--paper)',opacity:0}],{duration:280,easing:'ease-out',fill:'forwards'}).finished;
 }catch{
  swap();
 }finally{
  veil.hidden=true;veil.getAnimations().forEach(a=>a.cancel());button.removeAttribute('aria-busy');transitioning=false;
  $('message').focus({preventScroll:true});
 }
}
$('start').onclick=()=>scanner(true);$('back').onclick=()=>scanner(false);
$('about-open').onclick=()=>$('about').showModal();$('about-close').onclick=()=>$('about').close();
$('message').oninput=()=>{count();document.querySelectorAll('.example').forEach(b=>b.setAttribute('aria-pressed','false'));};
examples.forEach(([label,text])=>{let b=document.createElement('button');b.className='example';b.type='button';b.textContent=label;b.setAttribute('aria-pressed','false');b.onclick=()=>{document.querySelectorAll('.example').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));$('message').value=text;count();$('result').hidden=true;$('analyze-form').hidden=false;$('error').textContent='';$('message').removeAttribute('aria-invalid');};$('examples').append(b);});
function item(list,title,detail){let li=document.createElement('li');if(title){let strong=document.createElement('strong');strong.textContent=title;li.append(strong);}let p=document.createElement('p');p.textContent=detail;li.append(p);list.append(li);}
function render(data){
 $('verdict').textContent=data.verdict;$('result').className=data.state;if(typeof showResultMotion==='function')showResultMotion(data.state);$('explanation').textContent=data.state==='danger'?'This message has warning signs worth taking seriously.':data.state==='clear'?'No strong warning signs were found in this text.':'There isn’t enough clear evidence to trust this message.';$('next-action').textContent=data.recommendations[0] || 'Check the sender through a contact you already trust.';$('model-details').open=false;$('message-details').open=false;$('analyzed-message').textContent=$('message').value;
 $('assessment').textContent=`Model assessment: ${data.model_assessment}`;$('score').textContent=Math.round(data.spam_score*100);
 $('signals').replaceChildren();data.signals.forEach(s=>item($('signals'),s.title,s.detail));if(!data.signals.length)item($('signals'),'No rule-based warning signs','No listed pattern matched. This is not sender verification.');
 $('recommendations').replaceChildren();data.recommendations.slice(1).forEach(t=>item($('recommendations'),'',t));
 $('domains').textContent=data.domains.length?`Domains found (not visited): ${data.domains.join(', ')}`:'';
 $('feedback').querySelector('span').textContent='Was this analysis helpful?';$('feedback').querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed','false'));
 $('analyze-form').hidden=true;$('result').hidden=false;$('verdict').focus({preventScroll:true});$('result').scrollIntoView({behavior:reducedMotion()?'instant':'smooth',block:'nearest'});
}
$('analyze-form').onsubmit=e=>{e.preventDefault();const message=$('message').value.trim();if(message.length<3||message.length>6000){$('error').textContent='Paste between 3 and 6,000 characters to check.';$('message').setAttribute('aria-invalid','true');$('message').focus();return;}
 $('error').textContent='';$('message').removeAttribute('aria-invalid');$('check').disabled=true;$('check').textContent='Looking for red flags…';$('check').classList.add('is-loading');$('analysis-status').textContent='Checking the text and links. We won’t open any links.';$('message').readOnly=true;document.querySelectorAll('.example').forEach(b=>b.disabled=true);$('workbench').setAttribute('aria-busy','true');
 request=new XMLHttpRequest();request.open('POST','/api/analyze');request.setRequestHeader('Content-Type','application/json');request.timeout=30000;
 const finish=()=>{$('check').disabled=false;$('check').textContent='Spot the Red Flags';$('check').classList.remove('is-loading');$('analysis-status').textContent='';$('message').readOnly=false;document.querySelectorAll('.example').forEach(b=>b.disabled=false);$('workbench').removeAttribute('aria-busy');};
 request.onload=()=>{finish();try{const d=JSON.parse(request.responseText);if(request.status!==200)throw Error(d.error||'Analysis unavailable. Please try again.');render(d);}catch(err){$('error').textContent=err.message;}};
 request.onerror=()=>{finish();$('error').textContent='Could not connect. Please try again.';};request.ontimeout=()=>{finish();$('error').textContent='The check took too long. Please try again.';};request.send(JSON.stringify({message}));
};
$('again').onclick=()=>{if(typeof resultPlayer!=='undefined' && resultPlayer){resultPlayer.destroy();resultPlayer=null;}$('result').hidden=true;$('analyze-form').hidden=false;$('message').value='';document.querySelectorAll('.example').forEach(b=>b.setAttribute('aria-pressed','false'));$('error').textContent='';$('message').removeAttribute('aria-invalid');$('analyzed-message').textContent='';$('model-details').open=false;$('message-details').open=false;count();$('message').focus();};
document.querySelectorAll('[data-feedback]').forEach(b=>{b.setAttribute('aria-pressed','false');b.onclick=()=>{$('feedback').querySelector('span').textContent=b.dataset.feedback==='yes'?'Good to hear. Stay sharp out there.':'Fair enough. Double-check with the sender.';$('feedback').querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));};});
