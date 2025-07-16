// background.js
// IMPORTANT: importScripts() must be called at the top level, before any other complex logic.
try {
  // Path is relative to the root of the extension in the build directory.
  importScripts('lib/browser-polyfill.js'); 
} catch (e) {
  console.error('CRITICAL: Failed to import browser-polyfill.js. Extension will likely not work in Chrome.', e);
  // To prevent further 'browser is not defined' errors and to make it clear the polyfill failed:
  if (typeof browser === 'undefined') {
    // This is NOT a full polyfill, just a stub to potentially reduce console noise of 'browser is undefined'.
    // Functionality WILL BE BROKEN.
    globalThis.browser = globalThis.chrome || {}; 
    console.error("Polyfill failed to load. A minimal 'browser' object has been stubbed using 'chrome' or empty object.");
  }
}

// --- Notification Helper ---
async function showSystemNotification(title, message, success = true) {
  try {
    // Check if browser.notifications is available before using it
    if (typeof browser !== 'undefined' && browser.notifications) {
      const iconUrl = browser.runtime.getURL("icons/logo.png"); 
      await browser.notifications.create({
        type: 'basic', iconUrl: iconUrl, title: title, message: message
      });
    } else {
      console.warn('browser.notifications API not available. Cannot show system notification.');
    }
  } catch (err) {
    // console.error('Background: Error showing system notification:', err);
  }
}

// --- Logout and State Management ---
async function performLogoutCleanup(notifyUser = false) {
  if (typeof browser === 'undefined' || !browser.storage) return; // Guard clause
  // console.log('Background: Performing full logout cleanup...');
  await browser.storage.local.set({
    isLoggedIn: false,
    magnetLinksEnabled: false,
    torrentFilesEnabled: false,
    removeTorrentAfterUpload: false
  });
  await browser.storage.local.remove(['loggedInUsername']);
  if (notifyUser) {
    await showSystemNotification('Logged Out', 'You have been logged out and features disabled.', false);
  }
}

async function forceLogout() {
  // console.warn('Background: Forcing logout...');
  await performLogoutCleanup(true);
}

// --- Authentication & API Call Helper ---
async function attemptReLogin() {
  if (typeof browser === 'undefined' || !browser.storage) return false; // Guard clause
  // console.log('Background: Attempting re-login...');
  const creds = await browser.storage.local.get(['savedUsername', 'savedPassword', 'serverUrl']);
  if (!creds.savedUsername || !creds.savedPassword || !creds.serverUrl) {
    await forceLogout();
    return false;
  }
  try {
    const response = await fetch(`${creds.serverUrl}/login`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, mode: 'cors',
      credentials: 'include', body: JSON.stringify({ username: creds.savedUsername, password: creds.savedPassword })
    });
    if (response.ok) {
      await response.json();
      await browser.storage.local.set({ isLoggedIn: true, loggedInUsername: creds.savedUsername });
      return true;
    } else {
      await forceLogout();
      return false;
    }
  } catch (error) {
    await forceLogout();
    return false;
  }
}

async function fetchWithAuthRetry(url, options, isRetry = false) {
  if (typeof browser === 'undefined') { 
      console.error("fetchWithAuthRetry: 'browser' object not available. Cannot proceed.");
      return new Response(JSON.stringify({ error: "Extension context lost" }), { status: 500, statusText: "Extension context lost" });
  }
  let response = await fetch(url, options);
  if (response.status === 401 && !isRetry) {
    const reLoginSuccess = await attemptReLogin();
    if (reLoginSuccess) {
      return fetchWithAuthRetry(url, options, true); 
    } else {
      return response; 
    }
  }  
  return response;
}

// --- Message Listener (for Magnet Links & User Logout Request) ---
if (typeof browser !== 'undefined' && browser.runtime && browser.runtime.onMessage) {
  browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'MAGNET_LINK_CLICKED' && message.href) {
      const magnetName = decodeURIComponent(message.href.match(/dn=([^&]*)/)?.[1] || 'Unknown Torrent').replace(/\+/g, ' ');
      browser.storage.local.get(['isLoggedIn', 'loggedInUsername', 'magnetLinksEnabled', 'serverUrl'])
        .then(async storageData => {
          if (storageData.isLoggedIn && storageData.loggedInUsername && storageData.magnetLinksEnabled && storageData.serverUrl) {
            const payload = { magnet_link: message.href, target_user: storageData.loggedInUsername };
            const fetchOptions = { method: 'POST', headers: { 'Content-Type': 'application/json' }, mode: 'cors', credentials: 'include', body: JSON.stringify(payload) };
            return fetchWithAuthRetry(`${storageData.serverUrl}/add_magnet_link`, fetchOptions);
          } else {
            let reason = (!storageData.isLoggedIn) ? 'User not logged in.' : 'Magnet link handling not enabled.';
            if (!storageData.serverUrl) reason = 'Server URL not set.';
            return Promise.reject({ isLogicError: true, reason: reason });
          }
        })
        .then(async fetchResponse => ({ok: fetchResponse.ok, status: fetchResponse.status, statusText: fetchResponse.statusText, data: await fetchResponse.json()}))
        .then(parsedServerResponse => {
          if (!parsedServerResponse.ok) sendResponse({ success: false, message: `${magnetName}: ${parsedServerResponse.data.error || `Server error (${parsedServerResponse.status})`}` });
          else sendResponse({ success: true, message: `${magnetName} successfully sent to server.` });
        })
        .catch(error => {
          if (error.isLogicError) sendResponse({ success: false, message: `${magnetName}: ${error.reason}` });
          else if (error instanceof SyntaxError) sendResponse({ success: false, message: `${magnetName}: Error parsing server response.` });
          else sendResponse({ success: false, message: `${magnetName}: Processing error - ${error.message}` });
        });
      return true; 
    } else if (message.type === 'USER_LOGOUT_REQUESTED') {
      performLogoutCleanup(false)
        .then(() => sendResponse({ success: true, message: 'Logout cleanup done.'}))
        .catch(err => sendResponse({ success: false, message: 'Error during logout cleanup.'}));
      return true; 
    }
  });
} else {
  console.error("Background.js: browser.runtime.onMessage not available. Magnet/logout messages won't be handled.");
}

// --- .torrent File Download Handling ---
if (typeof browser !== 'undefined' && browser.downloads && browser.downloads.onChanged) {
  browser.downloads.onChanged.addListener(async (downloadDelta) => {
    if (downloadDelta.state && downloadDelta.state.current === 'complete') {
      let filenameForNotification = 'Downloaded file';
      try {
        const [downloadItem] = await browser.downloads.search({ id: downloadDelta.id });
        if (!downloadItem) return;
        filenameForNotification = downloadItem.filename || downloadItem.url.substring(downloadItem.url.lastIndexOf('/') + 1);
        if (!filenameForNotification.toLowerCase().endsWith('.torrent')) return;

        const prefs = await browser.storage.local.get([
          'isLoggedIn', 'loggedInUsername', 'torrentFilesEnabled', 'removeTorrentAfterUpload', 'serverUrl'
        ]);

        if (!prefs.isLoggedIn || !prefs.loggedInUsername) return;
        if (!prefs.torrentFilesEnabled) return;
        if (!prefs.serverUrl) return;
        
        const fileResponse = await fetch(downloadItem.url);
        if (!fileResponse.ok) throw new Error(`Failed to fetch .torrent file blob: ${fileResponse.statusText}`);
        const fileBlob = await fileResponse.blob();
        const formData = new FormData();
        formData.append('file', fileBlob, filenameForNotification);
        formData.append('target_user', prefs.loggedInUsername);

        const fetchOptions = { method: 'POST', mode: 'cors', credentials: 'include', body: formData };
        const serverResponse = await fetchWithAuthRetry(`${prefs.serverUrl}/add_torrent_file`, fetchOptions);
        const serverResponseData = await serverResponse.json();

        if (!serverResponse.ok) {
          const errorMsg = serverResponseData.error || `Server error (${serverResponse.status})`;
          await showSystemNotification('.torrent Upload Error', `${filenameForNotification}: ${errorMsg}`, false);
        } else {
          await showSystemNotification('.torrent Uploaded', `${filenameForNotification} successfully uploaded.`);
          if (prefs.removeTorrentAfterUpload) {
            try { await browser.downloads.removeFile(downloadDelta.id); } 
            catch (removeError) { /* console.error('Background: Failed to remove .torrent file:', removeError); */ await showSystemNotification('File Removal Error', `${filenameForNotification}: Could not be removed.`, false); }
          }
        }
      } catch (error) {
        const displayError = error.message || 'Unknown error.';
        if (!(error instanceof SyntaxError) && !error.message.toLowerCase().includes('failed to fetch') && !error.message.includes('User not logged in')) { 
          await showSystemNotification('.torrent Process Error', `Error with ${filenameForNotification}: ${displayError}`, false);
        }
      }
    }
  });
} else {
  console.error("Background.js: browser.downloads.onChanged not available. Torrent file downloads won't be handled.");
}

console.log("Service Worker: background.js script successfully loaded and top-level listeners attached.");