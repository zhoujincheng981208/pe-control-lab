/** 验证网页 JS 内核与 Python 内核逐项一致 */
const fs=require('fs'), cp=require('child_process'), path=require('path');
const py=JSON.parse(cp.execSync('python export_core.py',{cwd:__dirname}).toString().trim());
const html=fs.readFileSync(path.join(__dirname,'index.html'),'utf8');
const m=html.match(/<script id="core">([\s\S]*?)<\/script>/);
if(!m){console.error('未找到 core');process.exit(1);}
eval(m[1]);
const js=solve(DEMO);
let pass=0,fail=0; const TOL=1e-6;
const eq=(a,b)=>Math.abs(a-b)<=TOL*Math.max(1,Math.abs(b));
for(const k of ['L','R','Td','fsw','pm_max_rec']){
  const ok=eq(js[k],py[k]); console.log(`  [${ok?'OK':'XX'}] ${k.padEnd(12)} js=${js[k]} py=${py[k]}`); ok?pass++:fail++;
}
for(const n of ['保守','推荐','激进']){
  console.log(`\n===== ${n} =====`);
  const j=js.schemes[n], p=py[n];
  for(const k of Object.keys(p)){
    if(typeof p[k]!=='number'&&typeof p[k]!=='boolean') continue;
    const ok=(typeof p[k]==='boolean')?(j[k]===p[k]):eq(j[k],p[k]);
    console.log(`  [${ok?'OK':'XX'}] ${k.padEnd(10)} js=${j[k]} py=${p[k]}`); ok?pass++:fail++;
  }
}
console.log(`\n===== 合计 ${pass} 通过 / ${fail} 失败 =====`);
process.exit(fail?1:0);
