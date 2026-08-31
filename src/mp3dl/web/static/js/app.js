import { api, ensureTrackFromSearch } from "./api.js";
import { Player, formatTime } from "./player.js";

const YT_URL_RE = /^https?:\/\/(www\.)?(youtube\.com|youtu\.be)\//i;
const YT_PLAYLIST_RE = /[?&]list=([a-zA-Z0-9_-]+)/;

const state = {
  view: "search",
  playlistId: null,
  tracks: [],
  queueItems: [],
  playlists: [],
  searchResults: [],
  playingTrackId: null,
};

const els = {
  searchInput: document.getElementById("search-input"),
  playlistList: document.getElementById("playlist-list"),
  trackList: document.getElementById("track-list"),
  viewTitle: document.getElementById("view-title"),
  viewActions: document.getElementById("view-actions"),
  audio: document.getElementById("audio"),
  toast: document.getElementById("toast"),
  modal: document.getElementById("modal"),
  modalTitle: document.getElementById("modal-title"),
  modalBody: document.getElementById("modal-body"),
  modalCancel: document.getElementById("modal-cancel"),
  modalConfirm: document.getElementById("modal-confirm"),
};

const ui = {
  showToast(msg) {
    if (!msg) {
      els.toast.classList.add("hidden");
      return;
    }
    els.toast.textContent = msg;
    els.toast.classList.remove("hidden");
  },
  setPlaying(playing) {
    document.getElementById("btn-play").textContent = playing ? "⏸" : "▶";
  },
  updateNowPlaying(track) {
    state.playingTrackId = track?.id ?? null;
    document.getElementById("player-title").textContent = track?.title || "—";
    document.getElementById("player-artist").textContent = track?.channel || "—";
    const thumb = document.getElementById("player-thumb");
    if (track?.thumbnail) {
      thumb.src = track.thumbnail;
      thumb.style.visibility = "visible";
    } else {
      thumb.removeAttribute("src");
      thumb.style.visibility = "hidden";
    }
    renderTrackList();
  },
  updateProgress(cur, dur) {
    document.getElementById("time-current").textContent = formatTime(cur);
    document.getElementById("time-total").textContent = formatTime(dur);
    const bar = document.getElementById("seek-bar");
    bar.value = dur ? (cur / dur) * 100 : 0;
  },
};

const player = new Player(els.audio, ui);
player.setVolume(0.8);

function showModal(title, bodyHtml, onConfirm) {
  els.modalTitle.textContent = title;
  els.modalBody.innerHTML = bodyHtml;
  els.modal.classList.remove("hidden");
  return new Promise((resolve) => {
    const cleanup = () => {
      els.modal.classList.add("hidden");
      els.modalCancel.onclick = null;
      els.modalConfirm.onclick = null;
    };
    els.modalCancel.onclick = () => { cleanup(); resolve(false); };
    els.modalConfirm.onclick = async () => {
      const ok = onConfirm ? await onConfirm() : true;
      cleanup();
      resolve(ok);
    };
  });
}

function showContextMenu(x, y, items) {
  document.querySelectorAll(".context-menu").forEach((el) => el.remove());
  const menu = document.createElement("div");
  menu.className = "context-menu";
  menu.style.left = `${x}px`;
  menu.style.top = `${y}px`;
  items.forEach(({ label, action }) => {
    const btn = document.createElement("button");
    btn.textContent = label;
    btn.onclick = async () => {
      menu.remove();
      await action();
    };
    menu.appendChild(btn);
  });
  document.body.appendChild(menu);
  const close = (e) => {
    if (!menu.contains(e.target)) {
      menu.remove();
      document.removeEventListener("click", close);
    }
  };
  setTimeout(() => document.addEventListener("click", close), 0);
}

function trackMenuItems(track, extra = {}) {
  const items = [
    { label: "Putar", action: () => playTrackNow(track) },
    { label: "Tambah ke antrian", action: () => api.addToQueue(track.id).then(refreshQueue) },
    { label: "Download MP3", action: () => api.download(track.id).then(() => ui.showToast("Download dimulai")) },
  ];
  if (extra.removeFromPlaylist) {
    items.push({
      label: "Hapus dari playlist",
      action: () => api.removeFromPlaylist(state.playlistId, track.id).then(loadPlaylistTracks),
    });
  }
  if (state.playlists.length) {
    items.push({
      label: "Tambah ke playlist…",
      action: () => pickPlaylistAndAdd(track),
    });
  }
  return items;
}

async function pickPlaylistAndAdd(track) {
  const options = state.playlists.map((p) => `<option value="${p.id}">${p.name}</option>`).join("");
  await showModal(
    "Tambah ke playlist",
    `<select id="pick-playlist">${options}</select>`,
    async () => {
      const pid = Number(document.getElementById("pick-playlist").value);
      await api.addToPlaylist(pid, track.id);
      ui.showToast("Ditambahkan ke playlist");
      await loadPlaylists();
      return true;
    },
  );
}

function renderTrackRow(track, index, opts = {}) {
  const row = document.createElement("div");
  row.className = "track-row" + (state.playingTrackId === track.id ? " playing" : "");
  row.draggable = !!opts.draggable;
  row.dataset.trackId = track.id;
  if (opts.queueId) row.dataset.queueId = opts.queueId;

  const thumb = track.thumbnail
    ? `<img class="track-thumb" src="${track.thumbnail}" alt="">`
    : `<div class="track-thumb"></div>`;

  row.innerHTML = `
    <span class="drag-handle">${opts.draggable ? "⠿" : index + 1}</span>
    ${thumb}
    <div>
      <div class="track-title">${escapeHtml(track.title)}</div>
      <div class="track-artist">${escapeHtml(track.channel || "")}</div>
    </div>
    <div class="track-artist">${escapeHtml(track.channel || "")}</div>
    <div class="track-duration">${formatTime(track.duration)}</div>
    <button class="menu-btn" type="button">⋮</button>
  `;

  row.addEventListener("dblclick", () => playTrackNow(track));
  row.querySelector(".menu-btn").addEventListener("click", (e) => {
    e.stopPropagation();
    showContextMenu(e.clientX, e.clientY, trackMenuItems(track, opts));
  });

  if (opts.draggable) {
    row.addEventListener("dragstart", (e) => {
      e.dataTransfer.setData("text/plain", String(index));
      row.classList.add("dragging");
    });
    row.addEventListener("dragend", () => row.classList.remove("dragging"));
    row.addEventListener("dragover", (e) => e.preventDefault());
    row.addEventListener("drop", (e) => {
      e.preventDefault();
      const from = Number(e.dataTransfer.getData("text/plain"));
      const to = index;
      if (from !== to) opts.onReorder(from, to);
    });
  }

  return row;
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderTrackList() {
  els.trackList.innerHTML = "";
  let tracks = state.tracks;
  let draggable = false;
  let onReorder = null;

  if (state.view === "search") {
    tracks = state.searchResults.map((r) => ({ ...r, id: r._trackId, channel: r.channel }));
  } else if (state.view === "queue") {
    tracks = state.queueItems.map((q) => q.track);
    draggable = true;
    onReorder = reorderQueue;
  } else if (state.view === "playlist" && state.playlistId) {
    draggable = true;
    onReorder = reorderPlaylist;
  }

  if (!tracks.length) {
    els.trackList.innerHTML = '<div class="empty-state">Belum ada lagu di sini.</div>';
    return;
  }

  tracks.forEach((track, i) => {
    const opts = {
      draggable,
      onReorder,
      removeFromPlaylist: state.view === "playlist",
      queueId: state.view === "queue" ? state.queueItems[i]?.id : undefined,
    };
    els.trackList.appendChild(renderTrackRow(track, i, opts));
  });
}

async function playTrackNow(track) {
  let t = track;
  if (!t.id && t.url) {
    t = await ensureTrackFromSearch(track);
  }
  player.setQueue([t], 0);
  await player.playTrack(t);
}

async function playAllTracks(tracks) {
  if (!tracks.length) return;
  player.setQueue(tracks, 0);
  await player.playTrack(tracks[0]);
}

async function refreshQueue() {
  state.queueItems = await api.getQueue();
  if (state.view === "queue") {
    state.tracks = state.queueItems.map((q) => q.track);
    renderTrackList();
  }
}

async function loadPlaylists() {
  state.playlists = await api.getPlaylists();
  els.playlistList.innerHTML = "";
  state.playlists.forEach((p) => {
    const btn = document.createElement("button");
    btn.className = "nav-item playlist-item" + (state.playlistId === p.id ? " active" : "");
    btn.textContent = `♪ ${p.name}`;
    btn.onclick = () => setView("playlist", p.id, p.name);
    btn.addEventListener("contextmenu", (e) => {
      e.preventDefault();
      showContextMenu(e.clientX, e.clientY, [
        { label: "Putar semua", action: () => loadAndPlayPlaylist(p.id) },
        { label: "Tambah semua ke antrian", action: () => api.addPlaylistToQueue(p.id).then(refreshQueue) },
        { label: "Import playlist YouTube…", action: () => importToPlaylist(p.id) },
        { label: "Rename", action: () => renamePlaylist(p) },
        { label: "Hapus", action: () => api.deletePlaylist(p.id).then(loadPlaylists) },
      ]);
    });
    els.playlistList.appendChild(btn);
  });
}

async function loadPlaylistTracks() {
  if (!state.playlistId) return;
  state.tracks = await api.getPlaylistTracks(state.playlistId);
  renderTrackList();
}

async function loadAndPlayPlaylist(playlistId) {
  const tracks = await api.getPlaylistTracks(playlistId);
  player.setQueue(tracks, 0);
  await playAllTracks(tracks);
}

async function setView(view, playlistId = null, title = null) {
  state.view = view;
  state.playlistId = playlistId;
  document.querySelectorAll(".nav-item[data-view]").forEach((el) => {
    el.classList.toggle("active", el.dataset.view === view);
  });
  document.querySelectorAll(".playlist-item").forEach((el) => el.classList.remove("active"));

  els.viewActions.innerHTML = "";

  if (view === "search") {
    els.viewTitle.textContent = "Cari";
    state.tracks = [];
  } else if (view === "queue") {
    els.viewTitle.textContent = "Antrian";
    state.queueItems = await api.getQueue();
    state.tracks = state.queueItems.map((q) => q.track);
    const clearBtn = document.createElement("button");
    clearBtn.className = "btn secondary";
    clearBtn.textContent = "Kosongkan";
    clearBtn.onclick = () => api.clearQueue().then(refreshQueue).then(() => setView("queue"));
    els.viewActions.appendChild(clearBtn);
  } else if (view === "history") {
    els.viewTitle.textContent = "Riwayat";
    state.tracks = await api.getHistory();
  } else if (view === "playlist") {
    els.viewTitle.textContent = title || "Playlist";
    const playBtn = document.createElement("button");
    playBtn.className = "btn primary";
    playBtn.textContent = "Putar semua";
    playBtn.onclick = () => loadAndPlayPlaylist(playlistId);
    els.viewActions.appendChild(playBtn);
    await loadPlaylistTracks();
    return;
  }
  renderTrackList();
}

function reorderArray(arr, from, to) {
  const copy = arr.slice();
  const [item] = copy.splice(from, 1);
  copy.splice(to, 0, item);
  return copy;
}

async function reorderQueue(from, to) {
  const items = reorderArray(state.queueItems, from, to);
  await api.reorderQueue(items.map((q) => q.id));
  state.queueItems = items;
  state.tracks = items.map((q) => q.track);
  renderTrackList();
}

async function reorderPlaylist(from, to) {
  const tracks = reorderArray(state.tracks, from, to);
  await api.reorderPlaylist(state.playlistId, tracks.map((t) => t.id));
  state.tracks = tracks;
  renderTrackList();
}

async function runSearch(query) {
  if (YT_URL_RE.test(query)) {
    if (YT_PLAYLIST_RE.test(query) && state.playlists.length) {
      const pid = state.playlistId || state.playlists[0].id;
      const n = await api.importYoutubePlaylist(query, pid);
      ui.showToast(`Import ${n.added} lagu`);
      await loadPlaylists();
      if (state.playlistId) await loadPlaylistTracks();
      return;
    }
    const track = await api.createTrack(query);
    ui.showToast(`Ditambahkan: ${track.title}`);
    await playTrackNow(track);
    return;
  }
  state.searchResults = await api.search(query);
  state.view = "search";
  els.viewTitle.textContent = `Hasil: ${query}`;
  renderTrackList();
}

async function renamePlaylist(p) {
  await showModal(
    "Rename playlist",
    `<input id="rename-input" value="${escapeHtml(p.name)}">`,
    async () => {
      const name = document.getElementById("rename-input").value.trim();
      if (name) await api.renamePlaylist(p.id, name);
      await loadPlaylists();
      return true;
    },
  );
}

async function importToPlaylist(playlistId) {
  await showModal(
    "Import playlist YouTube",
    `<input id="import-url" placeholder="https://youtube.com/playlist?list=...">`,
    async () => {
      const url = document.getElementById("import-url").value.trim();
      if (!url) return false;
      const n = await api.importYoutubePlaylist(url, playlistId);
      ui.showToast(`Import ${n.added} lagu`);
      await loadPlaylists();
      if (state.playlistId === playlistId) await loadPlaylistTracks();
      return true;
    },
  );
}

let searchTimer;
els.searchInput.addEventListener("input", () => {
  clearTimeout(searchTimer);
  const q = els.searchInput.value.trim();
  if (!q) return;
  searchTimer = setTimeout(() => runSearch(q), 400);
});

els.searchInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    clearTimeout(searchTimer);
    runSearch(els.searchInput.value.trim());
  }
});

document.querySelectorAll(".nav-item[data-view]").forEach((btn) => {
  btn.onclick = () => setView(btn.dataset.view);
});

document.getElementById("btn-new-playlist").onclick = async () => {
  await showModal(
    "Playlist baru",
    `<input id="new-playlist-name" placeholder="Nama playlist">`,
    async () => {
      const name = document.getElementById("new-playlist-name").value.trim();
      if (!name) return false;
      await api.createPlaylist(name);
      await loadPlaylists();
      return true;
    },
  );
};

document.getElementById("btn-play").onclick = () => player.togglePlay();
document.getElementById("btn-next").onclick = () => player.playNext();
document.getElementById("btn-prev").onclick = () => player.playPrev();
document.getElementById("btn-shuffle").onclick = () => {
  const on = player.toggleShuffle();
  document.getElementById("btn-shuffle").classList.toggle("active", on);
};
document.getElementById("btn-repeat").onclick = () => {
  const mode = player.cycleRepeat();
  document.getElementById("btn-repeat").classList.toggle("active", mode !== "off");
  document.getElementById("btn-repeat").title = `Repeat: ${mode}`;
};
document.getElementById("btn-download").onclick = () => {
  if (player.currentTrack) {
    api.download(player.currentTrack.id).then(() => ui.showToast("Download dimulai"));
  }
};
document.getElementById("volume-bar").oninput = (e) => {
  player.setVolume(Number(e.target.value) / 100);
};
document.getElementById("seek-bar").oninput = (e) => {
  player.seek(Number(e.target.value) / 100);
};

document.getElementById("btn-settings").onclick = async () => {
  await showModal(
    "Settings",
    `<p>Download folder dikonfigurasi via <code>jjmp3 /setting</code> (CLI).</p>
     <button type="button" class="btn secondary" id="clear-cache">Hapus cache audio</button>`,
    async () => true,
  );
  document.getElementById("clear-cache")?.addEventListener("click", async () => {
    const r = await api.clearCache();
    ui.showToast(`Cache dibersihkan (${r.removed} file)`);
  });
};

async function init() {
  await loadPlaylists();
  await refreshQueue();
  setView("search");
}

init();
