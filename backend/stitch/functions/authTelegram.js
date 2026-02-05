exports = async function(loginPayload) {
  // This function is intended to be used as a "Custom Function Authentication" provider.
  // loginPayload is the object passed to Realm.App.logIn(Credentials.customFunction(payload))

  if (!loginPayload || !loginPayload.initData) {
    throw new Error("Missing initData");
  }

  const user = context.functions.execute("verifyTelegramAuth", loginPayload.initData);

  const telegramId = user.id.toString();

  // Return the user identity and custom data
  return {
    id: telegramId,
    name: user.first_name,
    data: {
        telegram_id: telegramId,
        username: user.username,
        first_name: user.first_name,
        photo_url: user.photo_url
    }
  };
};
