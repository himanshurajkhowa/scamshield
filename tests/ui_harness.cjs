// Small stateful DOM/XHR harness. It tests state transitions, not browser layout.
const fs = require('node:fs');
const vm = require('node:vm');
const { execFileSync } = require('node:child_process');

function createHarness({ revision, experience = false } = {}) {
  const state = { motionReduced: true, animationFrames: [], animationFailure: false };
  let document;
  class Node {
    constructor(tag = 'div') {
      Object.assign(this, {
        tag, children: [], attrs: {}, hidden: false, value: '',
        textContent: '', disabled: false, className: '',
      });
      this.classList = {
        add: name => this.updateClass(name, true),
        remove: name => this.updateClass(name, false),
        contains: name => this.className.split(/\s+/).includes(name),
      };
    }
    updateClass(name, present) {
      const names = new Set(this.className.split(/\s+/).filter(Boolean));
      if (present) names.add(name); else names.delete(name);
      this.className = [...names].join(' ');
    }
    setAttribute(key, value) { this.attrs[key] = value; }
    removeAttribute(key) { delete this.attrs[key]; }
    append(child) { this.children.push(child); }
    replaceChildren() { this.children = []; }
    focus() { document.activeElement = this; }
    scrollIntoView() {}
    getBoundingClientRect() { return { left: 40, top: 200, width: 190, height: 54 }; }
    animate(frames) {
      state.animationFrames.push(frames);
      return { finished: state.animationFailure ? Promise.reject(Error('Cancelled')) : Promise.resolve() };
    }
    getAnimations() { return []; }
    querySelectorAll(selector) { return this.children.filter(child => selector === 'button' && child.tag === 'button'); }
    querySelector(selector) { return this.children.find(child => child.tag === selector); }
  }
  const source = path => revision
    ? execFileSync('git', ['show', `${revision}:${path}`], { encoding: 'utf8' })
    : fs.readFileSync(path, 'utf8');
  const html = source('templates/index.html');
  const ids = {};
  for (const [, tag, id] of html.matchAll(/<([a-z0-9-]+)[^>]*\bid="([^"]+)"/g)) ids[id] = new Node(tag);
  const yes = new Node('button'), no = new Node('button'), feedbackText = new Node('span');
  yes.dataset = { feedback: 'yes' }; no.dataset = { feedback: 'no' };
  ids.feedback.children = [feedbackText, yes, no];
  ids.scanner.hidden = true; ids.result.hidden = true;
  document = {
    activeElement: null, documentElement: new Node('html'),
    getElementById: id => ids[id], createElement: tag => new Node(tag),
    querySelectorAll: selector => selector === '.example' ? ids.examples.children : selector === '[data-feedback]' ? [yes, no] : [],
  };
  document.documentElement.dataset = { theme: 'light' };
  class XHR {
    constructor() { XHR.latest = this; }
    open(method, url) { this.method = method; this.url = url; }
    setRequestHeader() {}
    send(body) { this.body = body; }
  }
  const session = new Map(), local = new Map();
  const storage = map => ({ getItem: key => map.get(key) || null, setItem: (key, value) => map.set(key, value) });
  const context = vm.createContext({
    document, Element: Node, XMLHttpRequest: XHR, innerWidth: 390, innerHeight: 844,
    window: { scrollTo() {}, matchMedia: () => ({ matches: state.motionReduced }) },
    sessionStorage: storage(session), localStorage: storage(local), setTimeout, clearTimeout, console,
  });
  vm.runInContext(source('public/static/app.js'), context);
  if (experience) vm.runInContext(source('public/static/experience.js'), context);
  return { ids, document, context, XHR, state, html, yes, no, session, local };
}
module.exports = { createHarness };
