const nativeHost = "dev.so1ve.chrome_url_router";

let nativePort;
let reconnectTimer;

async function openUrl(url) {
  let targetWindow;

  try {
    targetWindow = await chrome.windows.getLastFocused({
      windowTypes: ["normal"],
    });
  } catch {
    targetWindow = undefined;
  }

  if (targetWindow?.id === undefined) {
    await chrome.windows.create({
      focused: true,
      type: "normal",
      url,
    });
    return;
  }

  await chrome.tabs.create({
    active: true,
    url,
    windowId: targetWindow.id,
  });

  try {
    await chrome.windows.update(targetWindow.id, { focused: true });
  } catch {
    // The URL is already in the target window; compositor focus is best effort.
  }
}

function scheduleReconnect() {
  clearTimeout(reconnectTimer);
  reconnectTimer = setTimeout(connect, 1000);
}

function connect() {
  if (nativePort !== undefined) {
    return;
  }

  let connection;
  try {
    connection = chrome.runtime.connectNative(nativeHost);
  } catch {
    scheduleReconnect();
    return;
  }

  nativePort = connection;

  connection.onMessage.addListener((message) => {
    void (async () => {
      try {
        await openUrl(message.url);
        connection.postMessage({ ok: true });
      } catch (error) {
        connection.postMessage({
          error: String(error),
          ok: false,
        });
      }
    })();
  });

  connection.onDisconnect.addListener(() => {
    if (nativePort === connection) {
      nativePort = undefined;
    }
    scheduleReconnect();
  });
}

chrome.runtime.onInstalled.addListener(connect);
chrome.runtime.onStartup.addListener(connect);
connect();
