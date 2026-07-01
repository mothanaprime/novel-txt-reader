const fs=require('fs'), path=require('path');
const {JSDOM}=require('jsdom');
const ROOT=process.argv[2];
const label=process.argv[3]||ROOT;
let html=fs.readFileSync(path.join(ROOT,'开始阅读.html'),'utf8');
const catalog=fs.readFileSync(path.join(ROOT,'data/catalog.js'),'utf8');
html=html.replace('<script src="data/catalog.js"></script>','<script>'+catalog+'</script>');
function makeDom(seed){
  return new JSDOM(html,{runScripts:'dangerously',url:'http://localhost/index.html',pretendToBeVisual:true,
    beforeParse(win){
      if(seed) for(const k in seed) win.localStorage.setItem(k,seed[k]);
      const doc=win.document, oc=doc.createElement.bind(doc);
      doc.createElement=function(t){const el=oc(t);
        if(String(t).toLowerCase()==='script'){let _s='';
          Object.defineProperty(el,'src',{configurable:true,get(){return _s;},
            set(v){_s=v;setTimeout(()=>{try{const m=v.match(/data\/(.+)$/);
              el.dispatchEvent; win.eval(fs.readFileSync(path.join(ROOT,'data',m[1]),'utf8'));
              if(el.onload)el.onload();}catch(e){if(el.onerror)el.onerror(e);}},0);}});}
        return el;};
    }});
}
const wait=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
  const dom=makeDom(null), w=dom.window, d=w.document; await wait(300);
  let pass=0,fail=0; const ok=(c,m)=>{(c?pass++:fail++);console.log(`  ${c?'PASS':'FAIL'} | ${m}`);};
  const cat=w.__CATALOG__;
  const H=()=>{const h=d.querySelector('#article h1');return h?h.textContent:'';};
  console.log(`\n### ${label}  (title="${cat.title}", entries=${cat.entries.length})`);
  ok(d.title.includes(cat.title||'离线')||cat.title==='','document.title 含书名');
  ok(d.getElementById('bookTitle').textContent===(cat.title||''),'顶栏书名动态设置');
  ok(d.querySelectorAll('#tocList .tocItem').length===cat.entries.length,'目录条目='+cat.entries.length);
  ok(H().length>0,'首条渲染: '+H());
  ok(!/�/.test(d.getElementById('article').textContent),'正文无乱码');
  const before=H();
  d.getElementById('nextBtn').click(); await wait(150);
  ok(cat.entries.length<2 || H()!==before,'下一章可翻页: '+H());
  ok(JSON.parse(w.localStorage.getItem('fanren.v1.auto')).i>=0,'自动书签写入');
  d.getElementById('fabMark').click(); await wait(30);
  ok(JSON.parse(w.localStorage.getItem('fanren.v1.marks')||'[]').length===1,'手动书签写入');
  d.querySelector('#themeSeg [data-theme="night"]').click();
  ok(d.documentElement.getAttribute('data-theme')==='night','夜间主题');
  const seed={'fanren.v1.auto':w.localStorage.getItem('fanren.v1.auto'),
              'fanren.v1.settings':w.localStorage.getItem('fanren.v1.settings')};
  const savedI=JSON.parse(seed['fanren.v1.auto']).i;
  const dom2=makeDom(seed); await wait(300);
  const h2=dom2.window.document.querySelector('#article h1');
  ok(!!h2 && h2.textContent.length>0,'重开自动跳回 i='+savedI+' → '+(h2&&h2.textContent));
  return {pass,fail};
})().then(r=>{console.log(`  --> ${r.pass} passed, ${r.fail} failed`);process.exit(r.fail?1:0);})
   .catch(e=>{console.error('ERR',e);process.exit(2);});
