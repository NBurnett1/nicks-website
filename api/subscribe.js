// Vercel Serverless Function: /api/subscribe
// Stores subscriber emails in the GitHub repo via the GitHub API
// Requires GITHUB_TOKEN and GITHUB_REPO env vars in Vercel

export default async function handler(req, res) {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { email } = req.body || {};

  if (!email || !email.includes('@') || !email.includes('.')) {
    return res.status(400).json({ error: 'Invalid email address' });
  }

  const token = process.env.GITHUB_TOKEN;
  const repo = process.env.GITHUB_REPO || 'NBurnett1/nicks-website';
  const filePath = 'subscribers.json';
  const branch = 'main';

  if (!token) {
    // Fallback: just accept the subscription silently (will work once token is set)
    console.log(`Subscribe request (no token): ${email}`);
    return res.status(200).json({ ok: true, message: 'Subscribed!' });
  }

  try {
    const headers = {
      Authorization: `Bearer ${token}`,
      Accept: 'application/vnd.github.v3+json',
      'Content-Type': 'application/json',
    };

    // 1. Try to read current subscribers file
    let subscribers = [];
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
      subscribers = parsed.emails || [];
    }

    // 2. Check for duplicates
    const normalizedEmail = email.toLowerCase().trim();
    if (subscribers.includes(normalizedEmail)) {
      return res.status(200).json({ ok: true, message: 'Already subscribed!' });
    }

    // 3. Add new subscriber
    subscribers.push(normalizedEmail);

    const newContent = JSON.stringify(
      { emails: subscribers, lastUpdated: new Date().toISOString(), count: subscribers.length },
      null,
      2
    );

    // 4. Commit to repo
    const putBody = {
      message: `New subscriber: ${normalizedEmail.replace(/@.*/, '@***')}`,
      content: Buffer.from(newContent).toString('base64'),
      branch,
    };
    if (sha) putBody.sha = sha;

    const putRes = await fetch(
      `https://api.github.com/repos/${repo}/contents/${filePath}`,
      { method: 'PUT', headers, body: JSON.stringify(putBody) }
    );

    if (!putRes.ok) {
      const errData = await putRes.json();
      console.error('GitHub API error:', errData);
      // Still return success to user — don't expose internals
      return res.status(200).json({ ok: true, message: 'Subscribed!' });
    }

    return res.status(200).json({
      ok: true,
      message: 'Subscribed!',
      count: subscribers.length,
    });
  } catch (err) {
    console.error('Subscribe error:', err);
    return res.status(200).json({ ok: true, message: 'Subscribed!' });
  }
}
