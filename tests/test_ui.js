// DOM-adapter logic smoke test; this is not a visual browser test.
// Run with Node.js: node tests/test_ui.js (no npm dependencies).
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const html=fs.readFileSync(require('node:path').join(__dirname,'../index.html'),'utf8');
class Element {
 constructor(tag='DIV'){this.tagName=tag.toUpperCase();this.value='';this.checked=false;this.style={};this.children=[];this.options=[];this.disabled=false;this.readyState=0}
 append(...nodes){this.children.push(...nodes)}replaceChildren(...nodes){this.children=nodes}
 addEventListener(){}setPointerCapture(){}scrollTo(){}showModal(){}close(){}click(){this.onclick?.()}
 getBoundingClientRect(){return{left:0,top:0}}getContext(){return new Proxy({}, {get:(_,k)=>()=>{},set:()=>true})}
}
const elements={};
for(const match of html.matchAll(/<([\w-]+)\b([^>]*\bid="([^"]+)"[^>]*)>/g)){
 const e=new Element(match[1]);e.value=match[2].match(/\bvalue="([^"]*)"/)?.[1]||'';e.checked=/\bchecked\b/.test(match[2]);elements[match[3]]=e;
}
for(const match of html.matchAll(/<select\b[^>]*id="([^"]+)"[^>]*>([\s\S]*?)<\/select>/g)){
 elements[match[1]].options=[...match[2].matchAll(/<option(?:\s+value="([^"]*)")?[^>]*>([^<]*)<\/option>/g)].map(x=>({value:x[1]??x[2]}));
 elements[match[1]].value=elements[match[1]].options[0]?.value;
}
const sandbox={console,crypto:crypto.webcrypto,devicePixelRatio:1,performance:{now:()=>0},setTimeout:()=>0,clearTimeout(){},requestAnimationFrame(){},confirm:()=>true,Image:class{},fetch:async()=>({ok:true,json:async()=>({ffmpeg:true,ffprobe:true,workspace:'/tmp'})}),document:{getElementById:id=>{assert.ok(elements[id],'Missing DOM id '+id);return elements[id]},createElement:tag=>new Element(tag),body:new Element('BODY'),addEventListener(){}},window:{addEventListener(){}}};
vm.createContext(sandbox);vm.runInContext(html.match(/<script>([\s\S]*)<\/script>/)[1],sandbox);
const evaluate=code=>vm.runInContext(code,sandbox);
assert.equal(evaluate('p.count'),4);
evaluate('addText()');assert.equal(evaluate('p.layers.length'),1);assert.equal(evaluate('selectedLayer().kind'),'text');
evaluate('undo()');assert.equal(evaluate('p.layers.length'),0);evaluate('redo()');assert.equal(evaluate('p.layers.length'),1);
evaluate('selected=p.layers[0].id;inspect()');
elements.text.value='Halifax, NS';elements.w.value='500';elements.h.value='70';elements['apply-frame'].click();assert.equal(evaluate('p.layers[0].text'),'Halifax, NS');assert.equal(evaluate('p.layers[0].w'),500);
elements.duplicate.click();assert.equal(evaluate('p.layers.length'),2);elements.delete.click();assert.equal(evaluate('p.layers.length'),1);
// Nonfirst scene durations create sparse JS arrays; JSON must remain valid for the backend.
evaluate('scene=3');elements.duration.value='7.5';elements.duration.onchange();assert.equal(evaluate('seconds(0)'),5);assert.equal(evaluate('seconds(3)'),7.5);
// Dragging the selected frame preserves exact relative coordinates.
evaluate('selected=p.layers[0].id');const x=evaluate('p.layers[0].x'),y=evaluate('p.layers[0].y');
elements.stage.onpointerdown({button:0,clientX:(x+50)*.33,clientY:(y+20)*.33,pointerId:1});
elements.stage.onpointermove({clientX:(x+150)*.33,clientY:(y+70)*.33});elements.stage.onpointerup();
assert.equal(evaluate('p.layers[0].x'),x+100);assert.equal(evaluate('p.layers[0].y'),y+50);
// Asset IDs remain unique when an automatic layout returns known sources.
evaluate("assets=[{id:'a',kind:'image',name:'photo',width:300,height:200}]");
evaluate("acceptProject({project:p,assets:[{id:'a',kind:'image',name:'photo',width:300,height:200}]})");assert.equal(evaluate('assets.length'),1);
console.log('UI logic checks passed: DOM bindings, text, frame properties, undo/redo, duplicate/delete, sparse scene timing, drag, and media deduplication.');
