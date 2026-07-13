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
            <button onclick="likePost('${p.id}')">❤️ Like</button>
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
            <button onclick="likePost('${p.id}')">❤️ Like</button>
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