const { chromium } = require('playwright');
(async () => {
  const { serve } = await import('../scripts/serve.mjs');
  const { srv, url } = await serve(__dirname + '/dist', __dirname);
  const b = await chromium.launch({ args: (process.env.FLAGS||'').split(' ').filter(Boolean) });
  const mk = async () => { const p = await b.newPage(); await p.goto(url); await p.waitForFunction(() => window.READY); return p; };
  const p = await mk();
  console.log(await p.evaluate(() => { const g=document.createElement('canvas').getContext('webgl2'); const e=g.getExtension('WEBGL_debug_renderer_info'); return g.getParameter(e.UNMASKED_RENDERER_WEBGL); }));
  console.log(await p.evaluate(a => run(...a), [1080,1920,true,false,0,'basic']));
  const ps = [p, await mk(), await mk(), await mk()];
  const t = Date.now();
  const rs = await Promise.all(ps.map(q => q.evaluate(a => run(...a), [1080,1920,true,false,1,false])));
  console.log('4 parallel', rs.map(r=>r.blob), 'wall', Date.now()-t);
  await b.close(); srv.close();
})();
