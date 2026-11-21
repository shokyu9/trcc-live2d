import { defineConfig } from 'vite';
import { resolve } from 'node:path';
import { createRequire } from 'node:module';
import { readFileSync, existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
const req = createRequire(import.meta.url);
const v7 = createRequire(req.resolve('pixi7'));
export default defineConfig({ plugins: [{
  name: 'isolate-pixi-versions',
  enforce: 'pre',
  resolveId(id, importer) {
    if (!id.startsWith('@pixi/') || !importer) return null;
    let use7 = importer.includes('lipsyncpatch') || importer.includes('/pixi7/');
    let folder = dirname(importer);
    while (!use7 && folder.includes('node_modules')) {
      const file = join(folder, 'package.json');
      if (existsSync(file)) {
        const pkg = JSON.parse(readFileSync(file, 'utf8'));
        use7 = pkg.name?.startsWith('@pixi/') && pkg.version?.startsWith('7.');
        break;
      }
      folder = dirname(folder);
    }
    if (!use7) return null;
    const resolved = v7.resolve(id);
    return resolved.replace(/index\.js$/, 'index.mjs');
  }
}], build: { target: 'esnext', rollupOptions: { input: resolve(import.meta.dirname, 'renderer.html') } } });

