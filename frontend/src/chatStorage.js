const LEGACY_CHAT_CLEANUP_KEY = 'evidenceflow:chat:legacy-cleaned';

function getUserScope(user) {
  if (user?.id !== undefined && user?.id !== null) {
    return `id:${user.id}`;
  }

  const email = typeof user?.email === 'string' ? user.email.trim().toLowerCase() : '';
  return email ? `email:${email}` : 'unknown-user';
}

export function getChatStorageKeys(user) {
  const prefix = `evidenceflow:chat:${encodeURIComponent(getUserScope(user))}:`;
  return {
    scope: prefix,
    historyKey: `${prefix}history`,
    currentChatIdKey: `${prefix}current`,
    messagesPrefix: `${prefix}messages:`,
    freshLoginKey: `${prefix}fresh-on-login`,
  };
}

export function getChatMessagesKey(user, chatId) {
  return `${getChatStorageKeys(user).messagesPrefix}${encodeURIComponent(chatId)}`;
}

export function markFreshChatForLogin(user) {
  localStorage.setItem(getChatStorageKeys(user).freshLoginKey, 'true');
}

export function consumeFreshChatForLogin(user) {
  const key = getChatStorageKeys(user).freshLoginKey;
  const shouldStartFresh = localStorage.getItem(key) === 'true';
  localStorage.removeItem(key);
  return shouldStartFresh;
}

export function clearUserChatData(user) {
  const keys = getChatStorageKeys(user);
  Object.keys(localStorage).forEach(key => {
    if (key.startsWith(keys.messagesPrefix)) {
      localStorage.removeItem(key);
    }
  });
  localStorage.removeItem(keys.historyKey);
  localStorage.removeItem(keys.currentChatIdKey);
  localStorage.removeItem(keys.freshLoginKey);
}

export function clearLegacySharedChatData() {
  if (localStorage.getItem(LEGACY_CHAT_CLEANUP_KEY) === 'true') return;

  Object.keys(localStorage).forEach(key => {
    if (key === 'chatHistory' || key === 'currentChatId' || key.startsWith('chat_')) {
      localStorage.removeItem(key);
    }
  });
  localStorage.setItem(LEGACY_CHAT_CLEANUP_KEY, 'true');
}