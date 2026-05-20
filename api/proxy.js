module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  const { url } = req.query;
  if (!url) {
    return res.status(400).send('url parameter required');
  }

  try {
    const upstream = await fetch(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'application/xml, text/xml, */*',
        'Accept-Language': 'ko-KR,ko;q=0.9',
        'Referer': 'https://www.law.go.kr/',
      },
    });

    const text = await upstream.text();
    const contentType = upstream.headers.get('content-type') || 'text/plain; charset=utf-8';
    res.setHeader('Content-Type', contentType);
    return res.status(upstream.status).send(text);
  } catch (err) {
    return res.status(500).send(`Proxy error: ${err.message}`);
  }
};
