exports = function(initData) {
  const crypto = require('crypto');
  // NOTE: You must create a Value in App Services named "botToken" with your Telegram Bot Token.
  const botToken = context.values.get("botToken");

  if (!initData) {
    throw new Error("No initData provided");
  }

  const urlParams = new URLSearchParams(initData);
  const hash = urlParams.get('hash');
  urlParams.delete('hash');

  const dataCheckString = Array.from(urlParams.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([key, value]) => `${key}=${value}`)
    .join('\n');

  const secretKey = crypto.createHmac('sha256', 'WebAppData')
    .update(botToken)
    .digest();

  const calculatedHash = crypto.createHmac('sha256', secretKey)
    .update(dataCheckString)
    .digest('hex');

  if (calculatedHash !== hash) {
    throw new Error("Invalid hash");
  }

  // Check auth_date (optional but recommended)
  // const authDate = parseInt(urlParams.get('auth_date'));
  // const now = Math.floor(Date.now() / 1000);
  // if (now - authDate > 86400) throw new Error("Data is outdated");

  const user = JSON.parse(urlParams.get('user'));
  return user;
};
