// Dependency-free interaction regression test. Minimal DOM; Flask test client supplies real predictions.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {spawnSync} = require('node:child_process');
const { createHarness } = require('./ui_harness.cjs');
const { ids, document, context, XHR, state, html, yes, no } = createHarness();
(async()=>{
 assert.equal(ids.examples.children.length,6);
 for(const chip of ids.examples.children){ids.message.value='';chip.onclick();assert.ok(ids.message.value.length>5,'Every example fills on first click');}
 ids.message.value='';ids['analyze-form'].onsubmit({preventDefault(){}});assert.equal(ids.message.attrs['aria-invalid'],'true');assert.ok(ids.error.textContent);

 await ids.start.onclick();assert.equal(ids.scanner.hidden,false);assert.equal(state.animationFrames.length,0);assert.equal(document.activeElement,ids.message);
 ids.back.onclick();assert.equal(ids.landing.hidden,false);
 state.motionReduced=false;await ids.start.onclick();assert.equal(state.animationFrames.length,2);assert.equal(ids['scanner-reveal'].hidden,true);assert.equal(state.animationFrames[1][0].backgroundColor,'var(--terracotta)');assert.equal(state.animationFrames[1][1].backgroundColor,'var(--paper)');
 const chip=ids.examples.children[0];chip.onclick();assert.match(ids.message.value,/KYC/);assert.equal(chip.attrs['aria-pressed'],'true');
 ids['analyze-form'].onsubmit({preventDefault(){}});
 assert.equal(XHR.latest.method,'POST');assert.equal(XHR.latest.url,'/api/analyze');assert.equal(ids.check.disabled,true);assert.equal(ids.message.readOnly,true);assert.ok(ids.examples.children.every(x=>x.disabled));
 const response=spawnSync('.venv/bin/python',['-c',"import json,sys; from app import app; c=app.test_client(); r=c.post('/api/analyze',json=json.load(sys.stdin)); print(json.dumps({'status':r.status_code,'body':r.json}))"],{input:XHR.latest.body,encoding:'utf8'});
 assert.equal(response.status,0,response.stderr);const real=JSON.parse(response.stdout);XHR.latest.status=real.status;XHR.latest.responseText=JSON.stringify(real.body);XHR.latest.onload();
 assert.equal(ids.verdict.textContent,'Potential Scam');assert.equal(ids.result.hidden,false);assert.equal(ids.check.disabled,false);assert.equal(ids.message.readOnly,false);assert.equal(document.activeElement,ids.verdict);
 yes.onclick();assert.equal(yes.attrs['aria-pressed'],'true');no.onclick();assert.equal(yes.attrs['aria-pressed'],'false');assert.equal(no.attrs['aria-pressed'],'true');
 ids.again.onclick();assert.equal(ids.message.value,'');assert.equal(ids['analyze-form'].hidden,false);
 ids.message.value='Another ordinary test message';ids['analyze-form'].onsubmit({preventDefault(){}});XHR.latest.onerror();assert.match(ids.error.textContent,/connect/);assert.equal(ids.check.disabled,false);assert.ok(ids.examples.children.every(x=>!x.disabled));
 assert.doesNotMatch(html,/PromptWars|hackathon/i);assert.match(html,/Spot the Red Flags/);assert.match(html,/UCI/);
 const session = new Map(), local = new Map();
 const storage = map => ({getItem:key=>map.get(key)||null,setItem:(key,value)=>map.set(key,value)});
 context.sessionStorage=storage(session);context.localStorage=storage(local);
 let pendingTimer;context.setTimeout=fn=>{pendingTimer=fn;return 1;};context.clearTimeout=()=>{};
 document.documentElement={dataset:{theme:'light'}};
 let plays=[];
 context.window.lottie={loadAnimation:config=>{const events={};const player={addEventListener:(name,fn)=>events[name]=fn,destroy(){this.destroyed=true;},setSpeed(){},goToAndPlay(){this.played=true;}};plays.push({config,player,events});return player;}};
 vm.runInContext(fs.readFileSync('public/static/experience.js','utf8'),context);
 assert.equal(plays.length,0,'Boxer must not autoplay on welcome');
 assert.equal(ids.welcome.hidden,false);assert.equal(ids['app-shell'].inert,true);
 ids['welcome-go'].onclick();assert.equal(plays.length,1);assert.equal(plays[0].config.autoplay,false);assert.equal(plays[0].config.loop,false);
 plays[0].events.enterFrame({currentTime:29});assert.equal(ids['scam-word'].attrs['data-hit'],'false');plays[0].events.enterFrame({currentTime:30});assert.equal(ids['scam-word'].attrs['data-hit'],'true');
 plays[0].events.DOMLoaded();assert.equal(plays[0].player.played,true);plays[0].events.complete();pendingTimer();
 assert.equal(ids.welcome.hidden,true);assert.equal(session.get('scamshield-welcome'),'done');assert.equal(ids['app-shell'].inert,false);
 ids['replay-intro'].onclick();assert.equal(ids.welcome.hidden,false);assert.equal(ids['welcome-go'].disabled,false);assert.equal(ids['welcome-stage'].hidden,true);ids['welcome-skip'].onclick();
 ids['home-link'].onclick({preventDefault(){}});assert.equal(ids.welcome.hidden,false,'Logo intentionally replays intro');assert.equal(ids.scanner.hidden,true);assert.equal(ids['scam-word'].attrs['data-hit'],'false');ids['welcome-skip'].onclick();assert.equal(ids.landing.hidden,false);
 ids['welcome-theme'].onclick();assert.equal(local.get('scamshield-theme'),'dark');ids['welcome-theme'].onclick();
 ids['theme-toggle'].onclick();assert.equal(local.get('scamshield-theme'),'dark');assert.equal(ids['theme-toggle'].attrs['aria-pressed'],'true');

 // Native theme snapshots use the clicked toggle's centre and preserve storage in both directions.
 let transitions=0,themeAnimation;
 document.startViewTransition=update=>{transitions++;update();return {ready:Promise.resolve(),finished:Promise.resolve(),skipTransition(){}};};
 document.documentElement.animate=(frames,options)=>{themeAnimation={frames,options};return {finished:Promise.resolve()};};
 ids['welcome-theme'].getBoundingClientRect=()=>({left:10,top:20,width:44,height:44});
 await ids['welcome-theme'].onclick();assert.equal(local.get('scamshield-theme'),'light');assert.match(themeAnimation.frames[0].clipPath,/32px 42px/);assert.equal(themeAnimation.options.pseudoElement,'::view-transition-new(root)');
 await ids['theme-toggle'].onclick();assert.equal(local.get('scamshield-theme'),'dark');assert.match(themeAnimation.frames[0].clipPath,/135px 227px/);
 const beforeReduced=transitions;state.motionReduced=true;await ids['theme-toggle'].onclick();assert.equal(transitions,beforeReduced);assert.equal(local.get('scamshield-theme'),'light');state.motionReduced=false;
 document.startViewTransition=()=>{throw Error('Snapshot unavailable');};await ids['theme-toggle'].onclick();assert.equal(local.get('scamshield-theme'),'dark','Snapshot failure still applies theme');
 document.startViewTransition=update=>{transitions++;update();return {ready:Promise.resolve(),finished:Promise.resolve(),skipTransition(){}};};
 const firstToggle=ids['theme-toggle'].onclick();const ignoredToggle=ids['theme-toggle'].onclick();await Promise.all([firstToggle,ignoredToggle]);assert.equal(local.get('scamshield-theme'),'light','Rapid clicks do not overlap transitions');
 delete document.startViewTransition;await ids['theme-toggle'].onclick();assert.equal(local.get('scamshield-theme'),'dark','Older browsers retain direct toggle');
 vm.runInContext('window.ScamShieldExperience.initialize()',context);assert.equal(ids.welcome.hidden,true,'Returning session skips welcome');
 vm.runInContext("window.ScamShieldExperience.showResultMotion('clear')",context);assert.equal(plays.at(-1).config.path,'/static/animations/lock.json');
 plays.at(-1).events.complete();assert.equal(ids['result-motion'].attrs['data-complete'],'true');assert.match(ids['result-motion'].innerHTML,/rect/,'Completed low-risk state retains a static lock');assert.equal(ids['result-motion'].hidden,false);
 vm.runInContext("window.ScamShieldExperience.showResultMotion('danger')",context);assert.equal(ids['result-motion'].attrs['data-complete'],undefined);assert.equal(plays.at(-1).config.path,'/static/animations/boxer.json');
 for(const state of ['danger','caution','clear']){vm.runInContext(`window.ScamShieldExperience.showResultMotion('${state}')`,context);assert.equal(ids['result-icon'].attrs['data-status'],state);assert.match(ids['result-icon'].innerHTML,/<circle/);assert.doesNotMatch(ids['result-icon'].innerHTML,/<path/);}
 state.motionReduced=true;let count=plays.length;vm.runInContext("window.ScamShieldExperience.showResultMotion('danger')",context);assert.equal(plays.length,count,'Reduced motion must not play Lottie');
 session.clear();vm.runInContext('window.ScamShieldExperience.initialize()',context);ids['welcome-go'].onclick();assert.equal(plays.length,count);assert.equal(ids.welcome.hidden,true);
 session.clear();vm.runInContext('window.ScamShieldExperience.initialize()',context);ids['welcome-skip'].onclick();assert.equal(ids.welcome.hidden,true);assert.equal(session.get('scamshield-welcome'),'done');
 assert.doesNotMatch(html,/Explainable checks\. No links opened\./);assert.match(html,/Lightweight ML detection/);
 const css=fs.readFileSync('public/static/style.css','utf8');assert.match(css,/\.welcome-stage\[hidden\]\{display:block!important;visibility:hidden/,'Intro reserves its animation space');assert.match(css,/#welcome-title:focus,#verdict:focus\{outline:none/);assert.match(css,/:focus-visible\{outline-color:var\(--terracotta\)/,'Control focus rings remain');
 // Missing, intentionally excluded animation files must not block the public clone.
 state.motionReduced=false;session.clear();vm.runInContext('window.ScamShieldExperience.initialize()',context);ids['welcome-go'].onclick();plays.at(-1).events.data_failed();pendingTimer();assert.equal(ids.welcome.hidden,true,'Missing intro asset still enters the app');
 vm.runInContext("window.ScamShieldExperience.showResultMotion('clear')",context);plays.at(-1).events.data_failed();assert.equal(ids['result-motion'].attrs['data-complete'],'true','Missing lock asset retains static lock');
 vm.runInContext("window.ScamShieldExperience.showResultMotion('danger')",context);plays.at(-1).events.data_failed();assert.equal(ids['result-icon'].attrs['data-status'],'danger','Missing boxer retains labelled verdict indicator');
 assert.equal(ids['model-details'].open,false);assert.equal(ids['analyzed-message'].textContent,'');
 console.log('PASS: session welcome, click-only boxer, Skip/reduced-motion bypass, theme persistence, selective result animation.');
 console.log('PASS: reduced-motion and animated reveal, chips, loading locks, real Flask prediction, focus, feedback, reset, network error recovery, public copy. Minimal-DOM test; no visual layout assertions.');
})().catch(e=>{console.error(e);process.exitCode=1;});
