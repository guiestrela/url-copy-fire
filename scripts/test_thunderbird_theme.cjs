const fs = require('fs');
const vm = require('vm');
const assert = require('assert/strict');
const path = require('path');
const source = fs.readFileSync(path.join(__dirname,'thunderbird-theme.js'),'utf8');
(async () => {
 const values = new Map(); let update; let colors = {popup:'#19314a',popup_text:'#fceabc',popup_border:'#789abc'};
 const root = {dataset:{theme:'auto'},style:{setProperty:(k,v)=>values.set(k,v),removeProperty:k=>values.delete(k)}};
 const context = {document:{documentElement:root}, browser:{theme:{getCurrent:async()=>({colors}),onUpdated:{addListener:fn=>update=fn}},windows:{getCurrent:async()=>({id:7})}},console};
 vm.createContext(context); vm.runInContext(source, context);
 await context.applyThunderbirdTheme();
 assert.equal(values.get('--bg'),'#19314a'); assert.equal(values.get('--fg'),'#fceabc'); assert.equal(values.get('--border'),'#789abc');
 colors = {toolbar:[20,30,40],toolbar_text:'#eeeeee'}; await update({windowId:7});
 assert.equal(values.get('--bg'),'rgb(20,30,40)'); assert.equal(values.get('--fg'),'#eeeeee');
 root.dataset.theme='light'; await context.applyThunderbirdTheme(); assert.equal(values.size,0);
 root.dataset.theme='auto'; colors={}; await context.applyThunderbirdTheme(); assert.equal(values.size,0);
 console.log('PASS: custom palette, theme updates, RGB arrays, manual override, empty-theme fallback');
})().catch(e=>{console.error(e);process.exit(1)});
