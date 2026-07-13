// ---------- Tab Switching ----------
let currentSocialTab = 'friends';

function switchSocialTab(tab) {
  currentSocialTab = tab;
  document.getElementById('friendsFeed').style.display = tab === 'friends' ? 'block' : 'none';
  document.getElementById('newsFeed').style.display = tab === 'news' ? 'block' : 'none';
  document.getElementById('messagingPanel').style.display = 'none'; // close messaging
  document.getElementById('tabFriends').classList.toggle('active', tab === 'friends');
  document.getElementById('tabNews').classList.toggle('active', tab === 'news');
  if (tab === 'friends') loadFriendsFeed();
  else loadNewsFeed();
}

// ---------- Friends Feed ----------
async function loadFriendsFeed() {
  const container = document.getElementById('friendsPosts');
  const loading = document.getElementById('friendsLoading');
  try {
    const resp = await apiFetch('/api/social/feed');
    if (!resp.ok) throw new Error('Failed to load feed');
    const posts = await resp.json();
    if (posts.length === 0) {
      container.innerHTML = '<div class="placeholder">No posts from friends yet. Follow someone to see their updates!</div>';
    } else {
      container.innerHTML = posts.map(p => `
        <div class="card">
          <div class="post-author">${p.author_name || 'Unknown'}</div>
          <p>${p.content}</p>
          <div class="post-time">${new Date(p.created_at).toLocaleString()}</div>
          <div class="post-actions">
            <button onclick="likePost('${p.id}')">❤️ Like</button>
            <button onclick="commentPost('${p.id}')">💬 Comment</button>
            <button onclick="viewProfile('${p.author_id}')">👤 Profile</button>
          </div>
        </div>
      `).join('');
    }
    loading.style.display = 'none';
  } catch (e) {
    container.innerHTML = '<div class="placeholder">⚠️ Could not load posts. Please try again.</div>';
    loading.style.display = 'none';
  }
}

// ---------- lomiNews Feed ----------
async function loadNewsFeed() {
  const container = document.getElementById('newsPosts');
  const loading = document.getElementById('newsLoading');
  try {
    const resp = await apiFetch('/api/social/news');
    if (!resp.ok) throw new Error('Failed to load news');
    const posts = await resp.json();
    if (posts.length === 0) {
      container.innerHTML = '<div class="placeholder">No news posts yet. Subscribe to categories or follow newscasters!</div>';
    } else {
      container.innerHTML = posts.map(p => `
        <div class="card">
          <div class="post-author">${p.author_name || 'Newscaster'} <span class="badge-newscaster">Newscaster</span></div>
          <p>${p.content}</p>
          <div class="post-time">${new Date(p.created_at).toLocaleString()}</div>
          <div class="post-actions">
            <button onclick="likePost('${p.id}')">❤️ Like</button>
            <button onclick="commentPost('${p.id}')">💬 Comment</button>
            <button onclick="viewProfile('${p.author_id}')">👤 Profile</button>
          </div>
        </div>
      `).join('');
    }
    loading.style.display = 'none';
  } catch (e) {
    container.innerHTML = '<div class="placeholder">⚠️ Could not load news. Please try again.</div>';
    loading.style.display = 'none';
  }
}

// ---------- Messaging ----------
let currentChatPartner = null;

function openChat(partnerId, partnerName) {
  currentChatPartner = partnerId;
  document.getElementById('friendsFeed').style.display = 'none';
  document.getElementById('newsFeed').style.display = 'none';
  document.getElementById('messagingPanel').style.display = 'flex';
  document.getElementById('chatPartnerName').textContent = partnerName;
  loadChatMessages();
}

async function loadChatMessages() {
  const container = document.getElementById('chatMessages');
  container.innerHTML = '<p>Loading…</p>';
  try {
    const resp = await apiFetch('/api/social/messages/inbox', {
      headers: { 'Authorization': `Bearer ${getToken()}` }
    });
    const msgs = await resp.json();
    const partnerMsgs = msgs.filter(m => m.sender_uid === currentChatPartner || m.recipient_uid === currentChatPartner);
    container.innerHTML = partnerMsgs.map(m => `
      <div class="msg-bubble ${m.sender_uid === getCurrentUserId() ? 'sent' : 'received'}">
        <div>${m.body}</div>
        <div class="time">${new Date(m.created_at).toLocaleString()}</div>
      </div>
    `).join('');
  } catch (e) {
    container.innerHTML = '<p>Could not load messages.</p>';
  }
}

document.getElementById('btnChatSend').addEventListener('click', async () => {
  const body = document.getElementById('chatInput').value.trim();
  if (!body || !currentChatPartner) return;
  await apiFetch('/api/social/messages/send', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}` },
    body: JSON.stringify({ recipient_uid: currentChatPartner, body })
  });
  document.getElementById('chatInput').value = '';
  await loadChatMessages();
});

document.getElementById('btnBackFromChat').addEventListener('click', () => {
  document.getElementById('messagingPanel').style.display = 'none';
  if (currentSocialTab === 'friends') {
    document.getElementById('friendsFeed').style.display = 'block';
  } else {
    document.getElementById('newsFeed').style.display = 'block';
  }
});

// ---------- Actions ----------
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

async function viewProfile(uid) {
  try {
    const r = await apiFetch(`/api/social/profile/${uid}`);
    const profile = await r.json();
    document.getElementById('profileName').textContent = profile.full_name;
    document.getElementById('profileRole').textContent = profile.creator_role === 'newscaster' ? `Newscaster (${profile.news_category})` : 'Content Creator';
    document.getElementById('profilePosts').innerHTML = profile.posts.map(p => `<p>${p.content}</p>`).join('');
    document.getElementById('profileModal').style.display = 'flex';
  } catch (e) {
    alert('Could not load profile');
  }
}
document.getElementById('closeProfile').addEventListener('click', () => {
  document.getElementById('profileModal').style.display = 'none';
});

// ---------- New Post ----------
document.getElementById('btnPost').addEventListener('click', async () => {
  const content = document.getElementById('postContent').value.trim();
  if (!content) return;
  await apiFetch('/api/social/post', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}` },
    body: JSON.stringify({ content })
  });
  document.getElementById('postContent').value = '';
  loadFriendsFeed();
});

// ---------- Category Subscription (lomiNews) ----------
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

// Initial load
switchSocialTab('friends');