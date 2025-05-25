document.addEventListener('DOMContentLoaded', function() {
  const loginForm = document.getElementById('login-form');
  const savePasswordCheckbox = document.getElementById('save-password');
  const usernameInput = document.getElementById('username');
  const passwordInput = document.getElementById('password');
  const messageArea = document.getElementById('message-area');
  const loginContainer = document.getElementById('login-container');
  const successView = document.getElementById('success-view');
  const displayUsername = document.getElementById('display-username');
  const logoutButton = document.getElementById('logout-button');
  
  const magnetLinksEnabledCheckbox = document.getElementById('magnet-links-enabled');
  const torrentFilesEnabledCheckbox = document.getElementById('torrent-files-enabled');
  const removeTorrentAfterUploadCheckbox = document.getElementById('remove-torrent-after-upload');

  const SERVER_URL_PLACEHOLDER = '__SERVER_URL_PLACEHOLDER__'; // Build script will replace this

  function showMessage(message, isError = false) {
    messageArea.textContent = message;
    messageArea.style.color = isError ? 'red' : 'green';
  }

  async function populateLoginFormFromStorage() {
    try {
      const result = await browser.storage.local.get(['savedUsername', 'savedPassword']);
      usernameInput.value = result.savedUsername || '';
      passwordInput.value = result.savedPassword || '';
      savePasswordCheckbox.checked = !!result.savedPassword;
    } catch (err) {
      // showMessage(`Error loading saved credentials: ${err.message}`, true); // Optional: for dev
      usernameInput.value = ''; passwordInput.value = ''; savePasswordCheckbox.checked = false;
    }
  }

  async function showLoginView() {
    loginContainer.style.display = 'block';
    successView.style.display = 'none';
    messageArea.textContent = '';
    magnetLinksEnabledCheckbox.checked = false;
    torrentFilesEnabledCheckbox.checked = false;
    removeTorrentAfterUploadCheckbox.checked = false;
    removeTorrentAfterUploadCheckbox.disabled = true;
    await populateLoginFormFromStorage();
  }

  async function showSuccessView(username) {
    loginContainer.style.display = 'none';
    successView.style.display = 'block';
    if (displayUsername) displayUsername.textContent = username;
    messageArea.textContent = '';
    try {
      const prefs = await browser.storage.local.get([
        'magnetLinksEnabled', 'torrentFilesEnabled', 'removeTorrentAfterUpload'
      ]);
      magnetLinksEnabledCheckbox.checked = !!prefs.magnetLinksEnabled;
      torrentFilesEnabledCheckbox.checked = !!prefs.torrentFilesEnabled;
      removeTorrentAfterUploadCheckbox.checked = !!prefs.removeTorrentAfterUpload;
      removeTorrentAfterUploadCheckbox.disabled = !torrentFilesEnabledCheckbox.checked;
    } catch (err) {
      // showMessage(`Error loading preferences: ${err.message}`, true); // Optional: for dev
      magnetLinksEnabledCheckbox.checked = false;
      torrentFilesEnabledCheckbox.checked = false;
      removeTorrentAfterUploadCheckbox.checked = false;
      removeTorrentAfterUploadCheckbox.disabled = true;
    }
  }

  browser.storage.local.get(['isLoggedIn', 'loggedInUsername']).then(async (result) => {
    if (result.isLoggedIn && result.loggedInUsername) await showSuccessView(result.loggedInUsername);
    else await showLoginView();
  }).catch(async err => {
    // showMessage(`Error loading initial state: ${err.message}`, true); // Optional: for dev
    await showLoginView();
  });

  loginForm.addEventListener('submit', function(event) {
    event.preventDefault();
    messageArea.textContent = '';
    const currentUsername = usernameInput.value;
    const currentPassword = passwordInput.value;

    if (savePasswordCheckbox.checked) browser.storage.local.set({ savedUsername: currentUsername, savedPassword: currentPassword });
    else browser.storage.local.remove(['savedUsername', 'savedPassword']);

    fetch(`${SERVER_URL_PLACEHOLDER}/login`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, mode: 'cors',
      body: JSON.stringify({ username: currentUsername, password: currentPassword }), credentials: 'include'
    })
    .then(response => {
      if (!response.ok) return response.json().then(errData => Promise.reject(errData.error || `Login failed: ${response.statusText} (${response.status})`)).catch(() => Promise.reject(`Login failed: ${response.statusText} (${response.status})`));
      return response.json();
    })
    .then(data => browser.storage.local.set({
        isLoggedIn: true, loggedInUsername: currentUsername, 
        magnetLinksEnabled: false, torrentFilesEnabled: false, removeTorrentAfterUpload: false 
    }))
    .then(() => showSuccessView(currentUsername))
    .catch(errorMsg => showMessage(typeof errorMsg === 'string' ? errorMsg : 'Login error.', true));
  });

  logoutButton.addEventListener('click', function() {
    messageArea.textContent = '';
    fetch(`${SERVER_URL_PLACEHOLDER}/logout`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, mode: 'cors', credentials: 'include'
    }).catch(err => { /* console.warn('Server logout request failed.', err); */ }); 

    browser.runtime.sendMessage({ type: 'USER_LOGOUT_REQUESTED' })
      .then(async response => {
        // if (response && response.success) console.log('Popup: Background confirmed logout cleanup.');
        // else console.warn('Popup: Background logout cleanup failed or no ack.', response);
        await showLoginView();
      })
      .catch(async err => {
        // console.error('Popup: Error messaging background for logout:', err);
        await showLoginView(); 
      });
  });

  magnetLinksEnabledCheckbox.addEventListener('change', function() {
    browser.storage.local.set({ magnetLinksEnabled: this.checked });
    showMessage(`Magnet link handling ${this.checked ? 'enabled' : 'disabled'}.`, false);
    setTimeout(() => { if (messageArea.textContent.startsWith('Magnet link handling')) messageArea.textContent = ''; }, 3000);
  });

  torrentFilesEnabledCheckbox.addEventListener('change', function() {
    browser.storage.local.set({ torrentFilesEnabled: this.checked });
    removeTorrentAfterUploadCheckbox.disabled = !this.checked;
    if (!this.checked) {
      removeTorrentAfterUploadCheckbox.checked = false;
      browser.storage.local.set({ removeTorrentAfterUpload: false });
    }
    showMessage(`.torrent file handling ${this.checked ? 'enabled' : 'disabled'}.`, false);
    setTimeout(() => { if (messageArea.textContent.startsWith('.torrent file handling')) messageArea.textContent = ''; }, 3000);
  });

  removeTorrentAfterUploadCheckbox.addEventListener('change', function() {
    browser.storage.local.set({ removeTorrentAfterUpload: this.checked });
    showMessage(`Remove .torrent after upload ${this.checked ? 'enabled' : 'disabled'}.`, false);
    setTimeout(() => { if (messageArea.textContent.startsWith('Remove .torrent after upload')) messageArea.textContent = ''; }, 3000);
  });

});