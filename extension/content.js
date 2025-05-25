function showOnPageNotification(message, isSuccess, anchorElement) {
  document.querySelectorAll('[id^="magnet-ext-notification-"]').forEach(el => el.remove());
  const notificationId = 'magnet-ext-notification-' + Date.now();
  const div = document.createElement('div');
  div.id = notificationId;
  div.textContent = message;
  div.style.position = 'fixed'; div.style.zIndex = '2147483647'; div.style.padding = '12px 20px';
  div.style.borderRadius = '6px'; div.style.color = 'white'; div.style.fontSize = '15px';
  div.style.fontWeight = 'normal'; div.style.fontFamily = 'Arial, sans-serif';
  div.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
  div.style.transition = 'opacity 0.3s ease-in-out, transform 0.3s ease-in-out';
  div.style.opacity = '0'; div.style.transform = 'translateY(-20px)';
  div.style.backgroundColor = isSuccess ? '#28a745' : '#dc3545';
  div.style.top = '10px'; div.style.left = '10px';
  try { document.body.appendChild(div); } catch (e) { return; }
  void div.offsetWidth; // Force reflow
  div.style.opacity = '1'; div.style.transform = 'translateY(0px)';
  setTimeout(() => {
    div.style.opacity = '0'; div.style.transform = 'translateY(-20px)';
    setTimeout(() => { if (div.parentNode) div.parentNode.removeChild(div); }, 300);
  }, 4000);
}

function InterceptMagnetLinkClick(event) {
  event.preventDefault();
  event.stopImmediatePropagation();
  const clickedElement = event.currentTarget;
  const magnetHref = clickedElement ? clickedElement.href : null;
  if (!magnetHref) {
    // console.warn('Content script: InterceptMagnetLinkClick could not get magnet href.'); // Production: remove or make very discreet
    return; 
  }
  browser.runtime.sendMessage({ type: 'MAGNET_LINK_CLICKED', href: magnetHref })
    .then(response => {
      if (response && typeof response.success === 'boolean' && typeof response.message === 'string') {
        showOnPageNotification(response.message, response.success, null);
      } else {
        showOnPageNotification('Unexpected response from extension.', false, null);
      }
    })
    .catch(error => {
      showOnPageNotification(`Error: ${error.message || 'Could not connect to extension.'}`, false, null);
    });
}

function attachListenersToMagnetLinks() {
  const magnetLinks = document.querySelectorAll('a[href^="magnet:"]');
  magnetLinks.forEach(link => {
    link.removeEventListener('click', InterceptMagnetLinkClick, true);
    link.removeEventListener('click', InterceptMagnetLinkClick, false);
    link.addEventListener('click', InterceptMagnetLinkClick, true);
  });
}

function detachListenersFromMagnetLinks() {
  const magnetLinks = document.querySelectorAll('a[href^="magnet:"]');
  magnetLinks.forEach(link => {
    link.removeEventListener('click', InterceptMagnetLinkClick, true);
    link.removeEventListener('click', InterceptMagnetLinkClick, false);
  });
}

async function initializeMagnetLinkHandling() {
  try {
    const storageState = await browser.storage.local.get(['isLoggedIn', 'magnetLinksEnabled']);
    if (storageState.isLoggedIn && storageState.magnetLinksEnabled) {
      attachListenersToMagnetLinks();
    } else {
      detachListenersFromMagnetLinks();
    }
  } catch (err) {
    // console.error('Content script: Error during initialization, detaching listeners:', err); // Production: remove or make very discreet
    detachListenersFromMagnetLinks();
  }
}

initializeMagnetLinkHandling();

browser.storage.onChanged.addListener((changes, areaName) => {
  if (areaName === 'local' && (changes.isLoggedIn || changes.magnetLinksEnabled)) {
    initializeMagnetLinkHandling();
  }
});

const observer = new MutationObserver(() => {
  browser.storage.local.get(['isLoggedIn', 'magnetLinksEnabled']).then(storageState => {
    if (storageState.isLoggedIn && storageState.magnetLinksEnabled) {
      attachListenersToMagnetLinks(); 
    }
  }).catch(err => { /* console.error('Content script: Error in MutationObserver state check:', err); */ });
});

observer.observe(document.body, { childList: true, subtree: true });

// console.log('Content script active.'); // Final, simple load message if desired