// ===== SOCIAL WORKSPACE LOGIC (REAL API) =====
let currentSocialTab = 'friends';
let currentChatFriend = null;
let chatInterval = null;

function switchSocialTab(tab) {
  currentSocialTab = tab;
  document.getElementById('toggleFriends').classList.toggle('active', tab === 'friends');
  document.getElementById('toggleNews').classList.toggle('active', tab === 'news');
  document.getElementById('friendsTab').style.display = tab === 'friends' ? 'block' : 'none';
  document.getElementById('newsTab').style.display = tab === 'news' ? 'block' : 'none';
  document.getElementById('messagingPanel').style.display = 'none';
  if (tab === 'friends') loadFriendsFeed();
  else loadNewsFeed();
}

// --- Friends Feed (real API) ---
async function loadFriendsFeed() {
  const container = document.getElementById('friendsPosts');
  const loading = document.getElementById('friendsLoading');
  loading.style.display = 'block';
  try {
    const resp = await apiFetch('/api/social/feed', {
      headers: { 'Authorization': `Bearer ${getToken()}` }
    });
    if (!resp.ok) throw new Error('Failed');
    const posts = await resp.json();
    if (posts.length === 0) {
      container.innerHTML = '<div class="placeholder">No posts from friends yet. Follow someone to see their updates!</div>';
    } else {
      container.innerHTML = posts.map(p => `
        <div class="post-card">
          <div class="post-author">${p.author_name || 'Unknown'}</div>
          <div class="post-content">${p.content}</div>
          <div class="post-time">${new Date(p.created_at).toLocaleString()}</div>
          <div class="post-actions">
            <button onclick="likePost('${p.id}')">👍 Like</button>
            <button onclick="commentPost('${p.id}')">💬 Comment</button>
            <button onclick="viewProfile('${p.author_id}')">👤 Profile</button>
          </div>
        </div>
      `).join('');
    }
  } catch (e) {
    container.innerHTML = '<div class="placeholder">⚠️ Could not load posts. Please try again.</div>';
  } finally {
    loading.style.display = 'none';
  }
}

// --- News Feed (lomiNews, real API) ---
async function loadNewsFeed() {
  const container = document.getElementById('newsPosts');
  const loading = document.getElementById('newsLoading');
  const category = document.getElementById('newsCategory').value;
  loading.style.display = 'block';
  try {
    const url = category ? `/api/social/news?category=${encodeURIComponent(category)}` : '/api/social/news';
    const resp = await apiFetch(url, {
      headers: { 'Authorization': `Bearer ${getToken()}` }
    });
    if (!resp.ok) throw new Error('Failed');
    const posts = await resp.json();
    if (posts.length === 0) {
      container.innerHTML = '<div class="placeholder">No news posts yet.</div>';
    } else {
      container.innerHTML = posts.map(p => `
        <div class="post-card">
          <div class="post-author">${p.author_name || 'Newscaster'} <span class="badge-newscaster">Newscaster</span></div>
          <div class="post-content">${p.content}</div>
          <div class="post-time">${new Date(p.created_at).toLocaleString()}</div>
          <div class="post-actions">
            <button onclick="likePost('${p.id}')"> Like</button>
            <button onclick="commentPost('${p.id}')">💬 Comment</button>
            <button onclick="viewProfile('${p.author_id}')">👤 Profile</button>
          </div>
        </div>
      `).join('');
    }
  } catch (e) {
    container.innerHTML = '<div class="placeholder">⚠️ Could not load news. Please try again.</div>';
  } finally {
    loading.style.display = 'none';
  }
}

// --- Create Post ---
async function createPost() {
  const content = document.getElementById('postContent').value.trim();
  if (!content) return;
  try {
    const resp = await apiFetch('/api/social/post', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}` },
      body: JSON.stringify({ content })
    });
    if (resp.ok) {
      document.getElementById('postContent').value = '';
      loadFriendsFeed();
    } else {
      alert('Failed to post');
    }
  } catch (e) {
    alert('Network error');
  }
}

// --- Like & Comment ---
async function likePost(postId) {
  await apiFetch('/api/social/like', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}` },
    body: JSON.stringify({ post_id: postId })
  });
  loadFriendsFeed();
}

async function commentPost(postId) {
  const txt = prompt('Enter your comment:');
  if (!txt) return;
  await apiFetch('/api/social/comment', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}` },
    body: JSON.stringify({ post_id: postId, content: txt })
  });
  loadFriendsFeed();
}

// --- View Profile ---
async function viewProfile(uid) {
  try {
    const r = await apiFetch(`/api/social/profile/${uid}`, {
      headers: { 'Authorization': `Bearer ${getToken()}` }
    });
    const profile = await r.json();
    document.getElementById('profileName').textContent = profile.full_name;
    document.getElementById('profileRole').textContent = profile.creator_role === 'newscaster' ? `Newscaster (${profile.news_category})` : 'Content Creator';
    document.getElementById('profilePosts').innerHTML = profile.posts ? profile.posts.map(p => `<p>${p.content}</p>`).join('') : '';
    document.getElementById('profileModal').style.display = 'flex';
  } catch (e) {
    alert('Could not load profile');
  }
}
document.getElementById('closeProfile')?.addEventListener('click', () => {
  document.getElementById('profileModal').style.display = 'none';
});

// --- Friends Panel (open from FAB) ---
function openFriendsPanel() {
  document.getElementById('friendsPanel').classList.add('open');
  loadFriendsList();
}
function closeFriendsPanel() {
  document.getElementById('friendsPanel').classList.remove('open');
}

async function loadFriendsList() {
  const container = document.getElementById('friendsListContainer');
  container.innerHTML = '<p class="loading-text">Loading…</p>';
  try {
    const resp = await apiFetch('/api/social/friends', {
      headers: { 'Authorization': `Bearer ${getToken()}` }
    });
    if (!resp.ok) throw new Error('Failed');
    const friends = await resp.json();
    container.innerHTML = friends.map(f => `
      <div class="friend-item" onclick="openChat('${f.uid}', '${f.name}')">👤 ${f.name}</div>
    `).join('');
  } catch (e) {
    container.innerHTML = '<p>Could not load friends.</p>';
  }
}

// --- Messaging (real API) ---
function openChat(uid, name) {
  currentChatFriend = { uid, name };
  document.getElementById('chatPartnerName').textContent = name;
  document.getElementById('friendsTab').style.display = 'none';
  document.getElementById('newsTab').style.display = 'none';
  document.getElementById('messagingPanel').style.display = 'flex';
  document.getElementById('chatMessages').innerHTML = '';
  if (chatInterval) clearInterval(chatInterval);
  chatInterval = setInterval(loadChatMessages, 3000);
  loadChatMessages();
}

function closeChat() {
  currentChatFriend = null;
  document.getElementById('messagingPanel').style.display = 'none';
  if (currentSocialTab === 'friends') {
    document.getElementById('friendsTab').style.display = 'block';
  } else {
    document.getElementById('newsTab').style.display = 'block';
  }
  if (chatInterval) clearInterval(chatInterval);
}

async function loadChatMessages() {
  if (!currentChatFriend) return;
  const container = document.getElementById('chatMessages');
  try {
    const resp = await apiFetch('/api/social/messages/inbox', {
      headers: { 'Authorization': `Bearer ${getToken()}` }
    });
    const msgs = await resp.json();
    const partnerMsgs = msgs.filter(m => m.from_uid === currentChatFriend.uid || m.to_uid === currentChatFriend.uid);
    container.innerHTML = partnerMsgs.map(m => `
      <div class="msg ${m.from_uid === getCurrentUserId() ? 'sent' : 'received'}">
        <div>${m.text}</div>
        <div class="time">${new Date(m.created_at).toLocaleString()}</div>
      </div>
    `).join('');
    container.scrollTop = container.scrollHeight;
  } catch (e) {
    container.innerHTML = '<p>Could not load messages.</p>';
  }
}

document.getElementById('btnChatSend').addEventListener('click', async () => {
  const body = document.getElementById('chatInput').value.trim();
  if (!body || !currentChatFriend) return;
  await apiFetch('/api/social/messages/send', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}` },
    body: JSON.stringify({ target_uid: currentChatFriend.uid, text: body })
  });
  document.getElementById('chatInput').value = '';
  await loadChatMessages();
});

// --- Category Subscribe (News) ---
async function subscribeCategory(category) {
  try {
    const resp = await apiFetch('/api/social/news/subscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}` },
      body: JSON.stringify({ category })
    });
    if (resp.ok) {
      alert(`Subscribed to ${category} news!`);
      loadNewsFeed();
    } else {
      const err = await resp.json();
      alert(err.detail || 'Subscription failed');
    }
  } catch (e) {
    alert('Network error. Please try again.');
  }
}

// Helper: get current user ID (from JWT or stored)
function getCurrentUserId() {
  // Parse the JWT token (if stored) or return a placeholder
  const token = getToken();
  if (token) {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return payload.sub || 'me';
    } catch (e) {}
  }
  return 'me';
}

// Helper: get token (from localStorage)
function getToken() {
  return localStorage.getItem('lominii_token') || '';
}

// Initialise social on first load
switchSocialTab('friends');

/* ===== EPHEMERAL STATUS SYSTEM ===== */

// Load active friends' statuses and update the circle badge
async function loadStatusCircle() {
  try {
    const resp = await apiFetch('/api/social/status/friends');
    const data = await resp.json();
    const friends = data.friends;   // [{uid, name, media_type, expires_at}, ...]
    const badge = document.getElementById('statusBadge');
    const circle = document.getElementById('statusCircle');

    if (friends.length > 0) {
      badge.style.display = 'flex';
      badge.textContent = friends.length;
      circle.classList.add('has-active');
      buildStatusDropdown(friends);
    } else {
      badge.style.display = 'none';
      circle.classList.remove('has-active');
    }
  } catch (err) {
    // silently ignore – no connection or no friends
  }
}

// Build the dropdown list of friends with active statuses
function buildStatusDropdown(friends) {
  const dropdown = document.getElementById('statusDropdown');
  dropdown.innerHTML = friends.map(f => {
    const initials = f.name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
    return `
      <div class="status-friend" onclick="watchFriendStatus('${f.uid}')">
        <div class="avatar">${initials}</div>
        <div class="name">${f.name}</div>
        <div class="dot ${f.media_type}"></div>
      </div>
    `;
  }).join('');
}

// Toggle the dropdown
function openStatusDropdown() {
  document.getElementById('statusDropdown').classList.toggle('open');
}

// Watch a specific friend's statuses
async function watchFriendStatus(uid) {
  try {
    const resp = await apiFetch(`/api/social/status/friend/${uid}`);
    const data = await resp.json();
    const statuses = data.statuses;
    const viewer = document.getElementById('statusViewer');
    const content = document.getElementById('viewerContent');
    viewer.classList.add('open');
    playStatuses(statuses, content);
  } catch (err) {
    alert('Could not load statuses.');
  }
}

// Play statuses sequentially (simple version – you can enhance with swipe)
function playStatuses(statuses, container) {
  let index = 0;
  function showNext() {
    if (index >= statuses.length) {
      closeStatusViewer();
      return;
    }
    const s = statuses[index];
    if (s.media_type === 'text') {
      container.innerHTML = `<div class="viewer-text">${s.content}</div>`;
    } else if (s.media_type === 'voice') {
      container.innerHTML = `<audio controls src="${s.content}" style="width:100%"></audio>`;
    } else if (s.media_type === 'video') {
      container.innerHTML = `<video controls src="${s.content}" style="width:100%"></video>`;
    }
    index++;
    // auto‑advance after 5 seconds (adjust as needed)
    setTimeout(showNext, 5000);
  }
  showNext();
}

// Close the status viewer
function closeStatusViewer() {
  document.getElementById('statusViewer').classList.remove('open');
}

// Create a new status (triggered by the creator panel)
function createStatus() {
  const text = document.getElementById('statusText').value.trim();
  if (!text) return alert('Please write something.');
  const lifespanValues = [2, 24, 168, 720]; // hours
  const slider = document.getElementById('lifespanSlider');
  const hours = lifespanValues[slider.value];

  apiFetch('/api/social/status', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ media_type: 'text', content: text, lifespan_hours: hours })
  }).then(() => {
    document.getElementById('statusCreator').classList.remove('open');
    loadStatusCircle();   // refresh the circle badge
  }).catch(() => alert('Failed to create status.'));
}

// Open creator on long‑press of the circle
let longPressTimer;
document.getElementById('statusCircle').addEventListener('touchstart', (e) => {
  e.preventDefault();
  longPressTimer = setTimeout(() => {
    document.getElementById('statusCreator').classList.add('open');
  }, 600);  // 600ms long‑press
});
document.getElementById('statusCircle').addEventListener('touchend', () => {
  clearTimeout(longPressTimer);
});
// Also support mouse long‑press for desktop testing
document.getElementById('statusCircle').addEventListener('mousedown', (e) => {
  longPressTimer = setTimeout(() => {
    document.getElementById('statusCreator').classList.add('open');
  }, 600);
});
document.getElementById('statusCircle').addEventListener('mouseup', () => {
  clearTimeout(longPressTimer);
});

// Load the circle when the social tab becomes active
// (triggered from your tab switching logic – you can also call loadStatusCircle() when the social view is shown)
document.addEventListener('DOMContentLoaded', () => {
  // Initial load when page first opens (if social is default? No, but we can listen for tab switch)
  // We'll assume your dashboard.js calls a function when switching to social.
  // For now, we'll just load once after 2 seconds to give the app time to render.
  setTimeout(loadStatusCircle, 2000);
if (workspace === 'social') loadStatusCircle();

});

// If you have a function that's called whenever the social tab is activated, add loadStatusCircle() there.
// Example: if your dashboard.js has a switchToWorkspace function, add:
// if (workspace === 'social') loadStatusCircle();

/*===== SOCIAL WORKSPACE LOGIC (real API)===== */

let socialMode = 'feed';
let currentFriendUid = null;
let friends = [];

// Helper: call the social API
async function socialFetch(path, options = {}) {
  options.headers = { ...options.headers, 'Content-Type': 'application/json' };
  return apiFetch('/api/social' + path, options);
}

// Toggle status circle dropdown
document.getElementById('statusCircle').addEventListener('click', async () => {
  const dropdown = document.getElementById('friendDropdown');
  if (dropdown.style.display === 'block') {
    dropdown.style.display = 'none';
    return;
  }
  try {
    const resp = await socialFetch('/follows');
    const data = await resp.json();
    friends = data.followees;   // array of { uid, name, online }
    renderFriendDropdown();
    dropdown.style.display = 'block';
  } catch (err) {
    console.error('Could not load friends', err);
  }
});

function renderFriendDropdown() {
  const list = document.getElementById('friendList');
  list.innerHTML = friends.map(f => `
    <div class="friend-item" data-uid="${f.uid}">
      <span class="dot ${f.online ? 'online' : 'offline'}"></span>
      <span>${f.name}</span>
      <button class="btn-msg" onclick="event.stopPropagation(); openMessage('${f.uid}','${f.name}')">💬</button>
    </div>
  `).join('');
  list.querySelectorAll('.friend-item').forEach(item => {
    item.addEventListener('click', () => {
      const uid = item.dataset.uid;
      enterWatchMode(uid);
      document.getElementById('friendDropdown').style.display = 'none';
    });
  });
}

async function enterWatchMode(uid) {
  currentFriendUid = uid;
  const friend = friends.find(f => f.uid === uid);
  document.getElementById('watchFriendName').textContent = friend ? friend.name : 'Friend';
  document.getElementById('socialFeed').style.display = 'none';
  document.getElementById('watchMode').style.display = 'block';
  document.getElementById('statusCircle').style.transform = 'scale(0.5)';
  document.getElementById('statusCircle').style.top = '10px';
  document.getElementById('statusCircle').style.right = 'auto';
  document.getElementById('statusCircle').style.left = '10px';
  document.getElementById('switchLabel').textContent = 'Feed';
  socialMode = 'watch';
  try {
    const resp = await socialFetch('/posts/' + uid);
    const data = await resp.json();
    const posts = data.posts || [];
    document.getElementById('watchPosts').innerHTML = posts.map(p => `
      <div class="post-card">
        <div class="post-author">${p.author_name || friend?.name || 'Friend'}</div>
        <div class="post-content">${p.content}</div>
        <div class="post-time">${new Date(p.created_at).toLocaleString()}</div>
      </div>`).join('');
  } catch (err) {
    document.getElementById('watchPosts').innerHTML = '<p>Could not load posts.</p>';
  }
}

function toggleSocialMode() {
  if (socialMode === 'feed') {
    if (friends.length === 0) return;
    enterWatchMode(friends[0].uid);
  } else {
    document.getElementById('watchMode').style.display = 'none';
    document.getElementById('socialFeed').style.display = 'block';
    document.getElementById('statusCircle').style.transform = '';
    document.getElementById('statusCircle').style.top = '';
    document.getElementById('statusCircle').style.right = '';
    document.getElementById('statusCircle').style.left = '';
    document.getElementById('switchLabel').textContent = 'Watch';
    socialMode = 'feed';
  }
}

// Inline messaging – real calls
async function openMessage(uid, name) {
  document.getElementById('messageFriendName').textContent = name;
  document.getElementById('messageBox').style.display = 'flex';
  currentFriendUid = uid;
  try {
    const resp = await socialFetch('/messages/inbox');   // all messages; we'll filter by uid on frontend
    const data = await resp.json();
    const msgs = (data.messages || []).filter(m => m.from_uid === uid || m.to_uid === uid);
    document.getElementById('messageHistory').innerHTML = msgs.map(m => `
      <div class="msg ${m.from_uid === uid ? 'received' : 'sent'}">${m.text}</div>
    `).join('');
  } catch (err) {
    document.getElementById('messageHistory').innerHTML = '<p>Could not load messages.</p>';
  }
}
function closeMessage() {
  document.getElementById('messageBox').style.display = 'none';
}
async function sendSocialMessage() {
  const input = document.getElementById('messageInputSocial');
  const text = input.value.trim();
  if (!text) return;
  try {
    await socialFetch('/messages/send', {
      method: 'POST',
      body: JSON.stringify({ target_uid: currentFriendUid, text })
    });
    const history = document.getElementById('messageHistory');
    history.innerHTML += `<div class="msg sent">${text}</div>`;
    input.value = '';
  } catch (err) {
    console.error('Send failed', err);
  }
}