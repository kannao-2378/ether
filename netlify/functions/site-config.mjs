import { timingSafeEqual } from 'node:crypto';

const requiredModules = [
  '01-navigation',
  '02-hero',
  '03-ability',
  '04-cross-border-hero',
  '05-case-showcase',
  '06-organization-result',
  '07-data-result'
];

function response(statusCode, value) {
  return {
    statusCode,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'no-store'
    },
    body: JSON.stringify(value)
  };
}

function secretsMatch(received, expected) {
  if (!received || !expected) return false;
  const receivedBuffer = Buffer.from(received);
  const expectedBuffer = Buffer.from(expected);
  return receivedBuffer.length === expectedBuffer.length
    && timingSafeEqual(receivedBuffer, expectedBuffer);
}

function validateConfig(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  if (!value.modules || typeof value.modules !== 'object') return false;
  const serialized = JSON.stringify(value);
  const questionMarkCount = (serialized.match(/\?/g) || []).length;
  const chineseCharacterCount = (serialized.match(/[\u3400-\u9fff]/g) || []).length;
  if (questionMarkCount > 20 && chineseCharacterCount < 10) return false;
  return requiredModules.every((id) => value.modules[id]?.content && value.modules[id]?.motion);
}

export async function handler(event) {
  if (event.httpMethod !== 'POST') {
    return response(405, { error: '只允许确认保存请求。' });
  }

  const adminSecret = process.env.ADMIN_SECRET;
  const receivedSecret = event.headers['x-admin-secret'];
  if (!secretsMatch(receivedSecret, adminSecret)) {
    return response(401, { error: '后台密钥不正确。' });
  }

  const repository = process.env.GITHUB_REPOSITORY;
  const token = process.env.GITHUB_TOKEN;
  const branch = process.env.GITHUB_BRANCH || 'main';

  if (!repository || !token || !repository.includes('/')) {
    return response(500, { error: 'Netlify 尚未配置 GitHub 保存参数。' });
  }

  let config;
  try {
    config = JSON.parse(event.body || '');
  } catch {
    return response(400, { error: '配置内容不是有效 JSON。' });
  }

  if (!validateConfig(config)) {
    return response(400, { error: '配置结构不完整，已拒绝提交。' });
  }

  const apiUrl = `https://api.github.com/repos/${repository}/contents/config/site-config.json`;
  const headers = {
    Accept: 'application/vnd.github+json',
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
    'X-GitHub-Api-Version': '2022-11-28',
    'User-Agent': 'brand-portfolio-config'
  };

  const currentResponse = await fetch(`${apiUrl}?ref=${encodeURIComponent(branch)}`, { headers });
  if (!currentResponse.ok) {
    return response(502, { error: '无法读取 GitHub 上的当前配置。' });
  }

  const currentFile = await currentResponse.json();
  const updateResponse = await fetch(apiUrl, {
    method: 'PUT',
    headers,
    body: JSON.stringify({
      message: 'Update site configuration from admin',
      content: Buffer.from(`${JSON.stringify(config, null, 2)}\n`).toString('base64'),
      sha: currentFile.sha,
      branch
    })
  });

  if (!updateResponse.ok) {
    const details = await updateResponse.json().catch(() => ({}));
    return response(502, { error: details.message || 'GitHub 配置提交失败。' });
  }

  const result = await updateResponse.json();
  return response(200, {
    ok: true,
    mode: 'github',
    commit: result.commit?.html_url || null
  });
}
