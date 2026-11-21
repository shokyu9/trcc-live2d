import http from 'node:http';
import { readFile, realpath } from 'node:fs/promises';
import { createReadStream } from 'node:fs';
import { join, dirname, resolve, extname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { once } from 'node:events';
import { chromium } from 'playwright';

const [modelArg, coreArg, widthArg, heightArg, engineArg = "classic", backendArg = "software"] = process.argv.slice(2);
const modelFile = await realpath(modelArg);
const modelRoot = dirname(modelFile);
const coreFile = await realpath(coreArg);
const distRoot = resolve(dirname(fileURLToPath(import.meta.url)), 'dist');
const width = Math.max(160, Math.min(3072, Number(widthArg) || 480));
const height = Math.max(160, Math.min(3072, Number(heightArg) || 480));
const types = {'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.moc3':'application/octet-stream','.motion3.json':'application/json','.exp3.json':'application/json'};
async function safePath(root, sub) {
  const candidate = await realpath(join(root, decodeURIComponent(sub)));
  if (candidate !== root && !candidate.startsWith(root + '\\') && !candidate.startsWith(root + '/')) throw new Error('Path outside asset root');
  return candidate;
}
const server = http.createServer(async (request, response) => {
  try {
    const path = new URL(request.url, 'http://127.0.0.1').pathname;
    let file;
    if (path === '/core.js') file = coreFile;
    else if (path.startsWith('/model/')) file = await safePath(modelRoot, path.slice(7));
    else file = await safePath(distRoot, path === '/' ? 'renderer.html' : path.slice(1));
    response.writeHead(200, {'Content-Type': types[extname(file).toLowerCase()] || 'application/octet-stream', 'Cache-Control':'no-store'});
    createReadStream(file).pipe(response);
  } catch (error) {
    response.writeHead(404); response.end('Asset not found');
  }
});
server.listen(0, '127.0.0.1');
await once(server, 'listening');
const port = server.address().port;
let browser;
try {
  browser = await chromium.launch({headless:true, args:[
    '--disable-background-timer-throttling',
    ...(backendArg === 'hardware' ? [] : ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
  ]});
  const page = await browser.newPage({viewport:{width,height}, deviceScaleFactor:1});
  page.on('pageerror', error => process.stderr.write(`FATAL:${error.message}\n`));
  page.on('crash', () => process.stderr.write('FATAL:Chromium renderer crashed\n'));
  page.on('requestfailed', request => process.stderr.write(`REQUEST:${request.url()}:${request.failure()?.errorText}\n`));
  page.on('response', response => {
    if (!response.ok()) process.stderr.write(`HTTP:${response.status()}:${response.url()}\n`);
  });
  const url = `http://127.0.0.1:${port}/renderer.html?engine=${encodeURIComponent(engineArg)}&width=${width}&height=${height}&model=${encodeURIComponent(modelFile.split(/[\\/]/).at(-1))}`;
  await page.goto(url);
  await page.waitForFunction(() => window.rendererReady === true, null, {timeout:30000});
  await page.waitForTimeout(500);
  let telemetry = {temperature:null, warm:55, hot:75};
  let input = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => {
    input += chunk;
    const lines = input.split('\n'); input = lines.pop();
    for (const line of lines) { try { telemetry = JSON.parse(line); } catch (_) {} }
  });
  let stopping = false;
  const stop = () => { stopping = true; browser?.close().catch(() => {}); server.close(); };
  process.stdin.on('end', stop);
  process.on('SIGTERM', stop);
  process.on('SIGINT', stop);
  while (!stopping) {
    const started = Date.now();
    const encoded = await page.evaluate(value => {
      window.setTelemetry(value);
      return window.captureFrame();
    }, telemetry);
    const png = Buffer.from(encoded, 'base64');
    const header = Buffer.allocUnsafe(4); header.writeUInt32LE(png.length);
    if (!process.stdout.write(header)) await once(process.stdout, 'drain');
    if (!process.stdout.write(png)) await once(process.stdout, 'drain');
    await new Promise(resolve => setTimeout(resolve, Math.max(1, (1000 / Math.max(4, Math.min(30, Number(telemetry.options?.fps) || 8))) - (Date.now() - started))));
  }
} catch (error) {
  process.stderr.write(`FATAL:${error.stack || error}\n`);
  process.exitCode = 1;
} finally {
  await browser?.close();
  server.close();
}
