import { createServer } from 'node:http';
import { createReadStream } from 'node:fs';
import { readFile, rename, stat, writeFile } from 'node:fs/promises';
import { extname, join, normalize, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const projectRoot = fileURLToPath(new URL('.', import.meta.url));
const configPath = join(projectRoot, 'config', 'site-config.json');
const port = Number(process.env.PORT || 8001);
const host = process.env.HOST || '127.0.0.1';

const mimeTypes = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.mp4': 'video/mp4',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.webp': 'image/webp'
};

function getCorsHeaders(request) {
  const origin = request.headers.origin || '';
  const allowOrigin = /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(origin)
    ? origin
    : `http://${host}:${port}`;
  return {
    'Access-Control-Allow-Origin': allowOrigin,
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET, POST, PATCH, OPTIONS',
    Vary: 'Origin'
  };
}

function jsonResponse(request, response, statusCode, value) {
  response.writeHead(statusCode, {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
    ...getCorsHeaders(request)
  });
  response.end(JSON.stringify(value));
}

function validateConfig(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  if (!value.modules || typeof value.modules !== 'object') return false;
  const serialized = JSON.stringify(value);
  const questionMarkCount = (serialized.match(/\?/g) || []).length;
  const chineseCharacterCount = (serialized.match(/[\u3400-\u9fff]/g) || []).length;
  if (questionMarkCount > 20 && chineseCharacterCount < 10) return false;
  const requiredModules = [
    '01-navigation',
    '02-hero',
    '03-ability',
    '04-cross-border-hero',
    '05-case-showcase',
    '06-organization-result',
    '07-data-result'
  ];
  return requiredModules.every((id) => value.modules[id]?.content && value.modules[id]?.motion);
}

async function saveConfig(request, response) {
  let body = '';
  request.setEncoding('utf8');

  request.on('data', (chunk) => {
    body += chunk;
    if (body.length > 300_000) request.destroy();
  });

  request.on('end', async () => {
    try {
      const config = JSON.parse(body);
      if (!validateConfig(config)) {
        jsonResponse(request, response, 400, { error: '配置结构不完整，已拒绝写入。' });
        return;
      }

      const temporaryPath = `${configPath}.tmp`;
      await writeFile(temporaryPath, `${JSON.stringify(config, null, 2)}\n`, 'utf8');
      await rename(temporaryPath, configPath);
      jsonResponse(request, response, 200, { ok: true, mode: 'local', path: 'config/site-config.json' });
    } catch (error) {
      console.error(error);
      jsonResponse(request, response, 500, { error: '本地配置写入失败。' });
    }
  });
}

async function savePreviewSize(request, response) {
  let body = '';
  request.setEncoding('utf8');
  request.on('data', (chunk) => {
    body += chunk;
    if (body.length > 10_000) request.destroy();
  });
  request.on('end', async () => {
    try {
      const preview = JSON.parse(body);
      const width = Math.round(Number(preview.width));
      const height = Math.round(Number(preview.height));

      if (width < 320 || width > 1920 || height < 420 || height > 1200) {
        jsonResponse(request, response, 400, { error: '预览窗口尺寸超出允许范围。' });
        return;
      }

      const config = JSON.parse(await readFile(configPath, 'utf8'));
      config.preview = { width, height };
      const temporaryPath = `${configPath}.tmp`;
      await writeFile(temporaryPath, `${JSON.stringify(config, null, 2)}\n`, 'utf8');
      await rename(temporaryPath, configPath);
      jsonResponse(request, response, 200, { ok: true, preview: config.preview });
    } catch (error) {
      console.error(error);
      jsonResponse(request, response, 500, { error: '预览窗口尺寸保存失败。' });
    }
  });
}

function resolvePublicPath(pathname) {
  const decoded = decodeURIComponent(pathname);
  const relativePath = decoded === '/' ? 'index.html' : decoded.replace(/^\/+/, '');
  const candidate = resolve(projectRoot, normalize(relativePath));
  const resolvedRoot = resolve(projectRoot);
  return candidate === resolvedRoot || candidate.startsWith(`${resolvedRoot}${sep}`)
    ? candidate
    : null;
}

async function serveStatic(request, response) {
  const url = new URL(request.url, `http://${request.headers.host}`);
  const filePath = resolvePublicPath(url.pathname);

  if (!filePath) {
    response.writeHead(403);
    response.end('Forbidden');
    return;
  }

  try {
    const fileStat = await stat(filePath);
    const resolvedPath = fileStat.isDirectory() ? join(filePath, 'index.html') : filePath;
    const resolvedStat = fileStat.isDirectory() ? await stat(resolvedPath) : fileStat;
    const extension = extname(resolvedPath).toLowerCase();
    const contentType = mimeTypes[extension] || 'application/octet-stream';
    const cacheControl = resolvedPath.endsWith('site-config.json') ? 'no-store' : 'no-cache';
    const range = extension === '.mp4' ? request.headers.range : null;

    if (range) {
      const match = /^bytes=(\d*)-(\d*)$/.exec(range);
      const totalSize = resolvedStat.size;

      if (!match || (!match[1] && !match[2])) {
        response.writeHead(416, { 'Content-Range': `bytes */${totalSize}` });
        response.end();
        return;
      }

      const start = match[1]
        ? Number(match[1])
        : Math.max(0, totalSize - Number(match[2]));
      const requestedEnd = match[1] && match[2] ? Number(match[2]) : totalSize - 1;
      const end = Math.min(requestedEnd, totalSize - 1);

      if (!Number.isFinite(start) || !Number.isFinite(end) || start < 0 || start > end) {
        response.writeHead(416, { 'Content-Range': `bytes */${totalSize}` });
        response.end();
        return;
      }

      response.writeHead(206, {
        'Accept-Ranges': 'bytes',
        'Content-Range': `bytes ${start}-${end}/${totalSize}`,
        'Content-Length': end - start + 1,
        'Content-Type': contentType,
        'Cache-Control': cacheControl
      });

      if (request.method === 'HEAD') {
        response.end();
      } else {
        createReadStream(resolvedPath, { start, end }).pipe(response);
      }
      return;
    }

    const content = await readFile(resolvedPath);
    response.writeHead(200, {
      'Content-Type': contentType,
      'Content-Length': content.length,
      'Cache-Control': cacheControl,
      ...(extension === '.mp4' ? { 'Accept-Ranges': 'bytes' } : {})
    });
    response.end(request.method === 'HEAD' ? undefined : content);
  } catch {
    response.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
    response.end('Not Found');
  }
}

const server = createServer(async (request, response) => {
  if (request.method === 'OPTIONS' && request.url?.startsWith('/api/')) {
    response.writeHead(204, getCorsHeaders(request));
    response.end();
    return;
  }

  if (request.method === 'GET' && request.url === '/api/site-config') {
    jsonResponse(request, response, 200, { ok: true, mode: 'local' });
    return;
  }

  if (request.method === 'POST' && request.url === '/api/site-config') {
    await saveConfig(request, response);
    return;
  }

  if (request.method === 'PATCH' && request.url === '/api/preview-size') {
    await savePreviewSize(request, response);
    return;
  }

  if (request.method === 'GET' || request.method === 'HEAD') {
    await serveStatic(request, response);
    return;
  }

  response.writeHead(405, { Allow: 'GET, HEAD, POST' });
  response.end('Method Not Allowed');
});

server.listen(port, host, () => {
  console.log(`Brand Portfolio: http://${host}:${port}`);
  console.log(`配置后台: http://${host}:${port}/admin.html`);
});
