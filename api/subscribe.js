// Vercel Serverless Function: /api/subscribe
// Stores subscriber emails ENCRYPTED in the GitHub repo
// Requires: GITHUB_TOKEN, ENCRYPT_KEY env vars in Vercel

import crypto from 'crypto';

function encrypt(text, keyStr) {
  const key = crypto.createHash('sha256').update(keyStr).digest();
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
  let enc = cipher.update(text, 'utf8', 'hex') + cipher.final('hex');
  const tag = cipher.getAuthTag().toString('hex');
  return `${iv.toString('hex')}:${enc}:${tag}`;
}

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const { email } = req.body || {};
  if (!email || !email.includes('@') || !email.includes('.')) {
    return res.status(400).json({ error: 'Invalid email address' });
  }

  const token = process.env.GITHUB_TOKEN;
  const encryptKey = process.env.ENCRYPT_KEY;
  const repo = process.env.GITHUB_REPO || 'NBurnett1/nicks-website';
  const filePath = 'subscribers.json';
  const branch = 'main';

  if (!token || !encryptKey) {
    console.log(`Subscribe request (missing env vars): ${email}`);
    return res.status(200).json({ ok: true, message: 'Subscribed!' });
  }

  const normalizedEmail = email.toLowerCase().trim();

  try {
    const headers = {
      Authorization: `Bearer ${token}`,
      Accept: 'application/vnd.github.v3+json',
      'Content-Type': 'application/json',
    };

    // 1. Read current subscribers file
    let entries = [];
    let sha = null;

    const getRes = await fetch(
      `https://api.github.com/repos/${repo}/contents/${filePath}?ref=${branch}`,
      { headers }
    );

    if (getRes.ok) {
      const data = await getRes.json();
      sha = data.sha;
      const content = Buffer.from(data.content, 'base64').toString('utf8');
      const parsed = JSON.parse(content);
      entries = parsed.entries || [];
    }

    // 2. Check for duplicate (decrypt existing to compare)
    // We store a hash alongside the encrypted email for dedup without decrypting all
    const emailHash = crypto.createHash('sha256').update(normalizedEmail + encryptKey).digest('hex').slice(0, 16);

    if (entries.some(e => e.hash === emailHash)) {
      return res.status(200).json({ ok: true, message: 'Already subscribed!' });
    }

    // 3. Encrypt and store
    const encryptedEmail = encrypt(normalizedEmail, encryptKey);
    entries.push({ hash: emailHash, data: encryptedEmail });

    const newContent = JSON.stringify(
      { entries, lastUpdated: new Date().toISOString(), count: entries.length },
      null,
      2
    );

    // 4. Commit to repo
    const putBody = {
      message: `New subscriber #${entries.length}`,
      content: Buffer.from(newContent).toString('base64'),
      branch,
    };
    if (sha) putBody.sha = sha;

    const putRes = await fetch(
      `https://api.github.com/repos/${repo}/contents/${filePath}`,
      { method: 'PUT', headers, body: JSON.stringify(putBody) }
    );

    if (!putRes.ok) {
      console.error('GitHub API error:', await putRes.json());
      return res.status(200).json({ ok: true, message: 'Subscribed!' });
    }

    return res.status(200).json({ ok: true, message: 'Subscribed!', count: entries.length });
  } catch (err) {
    console.error('Subscribe error:', err);
    return res.status(200).json({ ok: true, message: 'Subscribed!' });
  }
}
