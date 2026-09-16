import { api, pollDownload } from "./api.js";
import { Player, formatTime } from "./player.js";

const state = {
  view: "library",
  playlistId: null,
  tracks: [],
  library: [],
  playlists: [],
  searchResults: [],
  settings: null,
  playingFilename: null,
  downloadJobs: {},
};

const els = {
  app: document.getElementById("app"),
  searchInput: document.getElementById("search-input"),
  searchForm: document.getElementById("search-form"),
  playlistList: document.getElementById("playlist-list"),
  trackList: document.getElementById("track-list"),
  editorPanel: document.getElementById("editor-panel"),
  settingsPanel: document.getElementById("settings-panel"),
  emptyState: document.getElementById("empty-state"),
  emptyCopy: document.getElementById("empty-copy"),
  viewTitle: document.getElementById("view-title"),
  viewEyebrow: document.getElementById("view-eyebrow"),
  viewActions: document.getElementById("view-actions"),
  pathChip: document.getElementById("path-chip"),
  audio: document.getElementById("audio"),
  toast: document.getElementById("toast"),
  modal: document.getElementById("modal"),
  modalTitle: document.getElementById("modal-title"),
  modalBody: document.getElementById("modal-body"),
  modalCancel: document.getElementById("modal-cancel"),
  modalConfirm: document.getElementById("modal-confirm"),
};

const reduceMotion =
  typeof matchMedia === "function" &&
  matchMedia("(prefers-reduced-motion: reduce)").matches;

const ui = {
  showToast(msg) {
    if (!msg) {
      els.toast.classList.add("hidden");
      return;
    }
    els.toast.textContent = msg;
    els.toast.classList.remove("hidden");
    clearTimeout(ui._toastTimer);
    ui._toastTimer = setTimeout(() => els.toast.classList.add("hidden"), 2800);
  },
  setPlaying(playing) {
    const btn = document.getElementById("btn-play");
    btn.querySelector(".icon-play").classList.toggle("hidden", playing);
    btn.querySelector(".icon-pause").classList.toggle("hidden", !playing);
    btn.setAttribute("aria-label", playing ? "Pause" : "Play");
  },
  updateNowPlaying(track) {
    state.playingFilename = track?.filename ?? null;
    document.getElementById("player-title").textContent = track?.title || "Nothing playing";
    document.getElementById("player-artist").textContent =
      track?.channel || track?.filename || "Local library";
    const thumb = document.getElementById("player-thumb");
    const url = track?.cover_url || (track?.cover ? api.coverUrl(track.cover) : null);
    if (url) {
      thumb.src = url;
      thumb.alt = track.title || "";
    } else {
      thumb.removeAttribute("src");
      thumb.alt = "";
    }
    highlightPlaying();
  },
  updateProgress(cur, dur) {
    document.getElementById("time-current").textContent = formatTime(cur);
    document.getElementById("time-total").textContent = formatTime(dur);
    const bar = document.getElementById("seek-bar");
    if (document.activeElement !== bar) {
      bar.value = dur ? (cur / dur) * 100 : 0;
    }
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
    els.modalCancel.onclick = () => {
      cleanup();
      resolve(false);
    };
    els.modalConfirm.onclick = async () => {
      const ok = onConfirm ? await onConfirm() : true;
      if (ok === false) return;
      cleanup();
      resolve(true);
    };
  });
}

function showContextMenu(x, y, items) {
  document.querySelectorAll(".context-menu").forEach((el) => el.remove());
  const menu = document.createElement("div");
  menu.className = "context-menu";
  menu.style.left = `${x}px`;
  menu.style.top = `${y}px`;
  items.forEach(({ label, action, danger }) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = label;
    if (danger) btn.style.color = "var(--danger)";
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

function formatDuration(sec) {
  return formatTime(sec);
}

function animateView() {
  if (reduceMotion || typeof gsap === "undefined") return;
  gsap.fromTo(
    "#main",
    { autoAlpha: 0.65, y: 12 },
    { autoAlpha: 1, y: 0, duration: 0.2, ease: "power2.out" }
  );
}

function runIntro() {
  if (reduceMotion || typeof gsap === "undefined") {
    els.app.dataset.ready = "true";
    return;
  }
  const tl = gsap.timeline({
    defaults: { ease: "power2.out" },
    onComplete: () => {
      els.app.dataset.ready = "true";
    },
  });
  gsap.set(".deck", { autoAlpha: 0, scale: 0.97 });
  tl.to(".deck", { autoAlpha: 1, scale: 1, duration: 0.45 }).from(
    ".sidebar, .topbar, .main, .player",
    { autoAlpha: 0, y: 10, duration: 0.28, stagger: 0.05 },
    "-=0.2"
  );
}

async function refreshSettings() {
  state.settings = await api.settings();
  const dir = state.settings.download_dir || "";
  els.pathChip.textContent = dir;
  els.pathChip.title = dir;
  const ver = state.settings.version;
  const verEl = document.getElementById("app-version");
  if (verEl && ver) {
    verEl.textContent = `v${ver}`;
  }
  if (ver) {
    document.title = `JJMP3 v${ver} — Local Deck`;
  }
}

async function refreshLibrary() {
  const data = await api.library();
  state.library = data.tracks || [];
  if (data.download_dir) {
    els.pathChip.textContent = data.download_dir;
    els.pathChip.title = data.download_dir;
  }
}

async function refreshPlaylists() {
  state.playlists = await api.playlists();
  renderPlaylists();
}

function renderPlaylists() {
  els.playlistList.innerHTML = "";
  state.playlists.forEach((pl) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "nav-item";
    if (state.view === "playlist" && state.playlistId === pl.id) {
      btn.classList.add("active");
    }
    btn.innerHTML = `<span class="nav-icon" aria-hidden="true">♪</span>${escapeHtml(pl.name)}`;
    btn.onclick = () => setView("playlist", pl.id);
    btn.oncontextmenu = (e) => {
      e.preventDefault();
      showContextMenu(e.clientX, e.clientY, [
        {
          label: "Edit playlist",
          action: () => setView("editor", pl.id),
        },
        {
          label: "Rename",
          action: async () => {
            const name = prompt("Playlist name", pl.name);
            if (!name?.trim()) return;
            await api.renamePlaylist(pl.id, name.trim());
            await refreshPlaylists();
          },
        },
        {
          label: "Delete playlist",
          danger: true,
          action: async () => {
            const ok = await showModal(
              "Delete playlist?",
              `<p>Remove <strong>${escapeHtml(pl.name)}</strong>? Files stay on disk.</p>`
            );
            if (!ok) return;
            await api.deletePlaylist(pl.id);
            if (state.playlistId === pl.id) setView("library");
            await refreshPlaylists();
          },
        },
      ]);
    };
    els.playlistList.appendChild(btn);
  });
}

function escapeHtml(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function coverFor(track) {
  if (track.cover_url) return track.cover_url;
  if (track.cover) return api.coverUrl(track.cover);
  return null;
}

function trackRowEl(track, { badge, progress, onPrimary, actions } = {}) {
  const row = document.createElement("div");
  row.className = "track-row";
  row.setAttribute("role", "listitem");
  if (track.filename && track.filename === state.playingFilename) {
    row.classList.add("playing");
  }

  const coverUrl = coverFor(track);
  const cover = document.createElement(coverUrl ? "img" : "div");
  cover.className = coverUrl ? "track-cover" : "track-cover placeholder";
  if (coverUrl) {
    cover.src = coverUrl;
    cover.alt = "";
    cover.loading = "lazy";
  } else {
    cover.textContent = "MP3";
  }

  const info = document.createElement("div");
  info.className = "track-info";
  info.innerHTML = `<div class="track-title">${escapeHtml(track.title || track.filename)}</div>
    <div class="track-sub">${escapeHtml(track.channel || track.filename || "")}</div>
    ${progress != null ? `<div class="progress-pill"><span style="width:${progress}%"></span></div>` : ""}`;

  const meta = document.createElement("div");
  meta.className = "track-meta";
  meta.textContent = track.duration != null ? formatDuration(track.duration) : "";

  const right = document.createElement("div");
  right.className = "row-actions";
  if (badge) {
    const b = document.createElement("span");
    b.className = `badge${badge.warn ? " warn" : ""}`;
    b.textContent = badge.text;
    right.appendChild(b);
  }
  (actions || []).forEach((a) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "icon-btn";
    btn.title = a.title;
    btn.innerHTML = a.icon;
    btn.onclick = (e) => {
      e.stopPropagation();
      a.action();
    };
    right.appendChild(btn);
  });

  row.append(cover, info, meta, right);
  row.onclick = () => onPrimary?.(track);
  row.oncontextmenu = (e) => {
    e.preventDefault();
    if (!actions?.length) return;
    showContextMenu(
      e.clientX,
      e.clientY,
      actions.map((a) => ({ label: a.title, action: a.action, danger: a.danger }))
    );
  };
  return row;
}

function highlightPlaying() {
  document.querySelectorAll(".track-row").forEach((el) => {
    el.classList.toggle(
      "playing",
      Boolean(state.playingFilename) && el.dataset.filename === state.playingFilename
    );
  });
}

function playableQueueFrom(list) {
  return list.filter((t) => t.filename);
}

async function playLocal(track, queue = null) {
  const q = queue || playableQueueFrom(state.tracks.length ? state.tracks : state.library);
  const idx = q.findIndex((t) => t.filename === track.filename);
  player.setQueue(q, idx >= 0 ? idx : 0);
  await player.playTrack(track);
}

function setNavActive() {
  document.querySelectorAll(".nav-item[data-view]").forEach((btn) => {
    const view = btn.dataset.view;
    btn.classList.toggle(
      "active",
      view === state.view || (view === "settings" && state.view === "settings")
    );
  });
  renderPlaylists();
}

async function setView(view, playlistId = null) {
  state.view = view;
  state.playlistId = playlistId;
  els.editorPanel.classList.add("hidden");
  els.settingsPanel.classList.add("hidden");
  els.trackList.classList.remove("hidden");
  els.emptyState.classList.add("hidden");
  els.viewActions.innerHTML = "";
  setNavActive();
  animateView();

  if (view === "library") {
    els.viewEyebrow.textContent = "Collection";
    els.viewTitle.textContent = "Library";
    await refreshLibrary();
    state.tracks = state.library;
    renderTrackList(state.library, {
      empty: "No tracks yet. Search and download your first MP3.",
      onPrimary: (t) => playLocal(t, state.library),
      actionsFor: libraryActions,
    });
  } else if (view === "explorer") {
    els.viewEyebrow.textContent = "Filesystem";
    els.viewTitle.textContent = "Explorer";
    await refreshLibrary();
    state.tracks = state.library;
    const path = state.settings?.download_dir || "";
    els.viewActions.innerHTML = `<span class="path-chip" title="${escapeHtml(path)}">${escapeHtml(path)}</span>`;
    renderTrackList(state.library, {
      empty: "This download folder has no MP3 files.",
      onPrimary: (t) => playLocal(t, state.library),
      actionsFor: libraryActions,
      showFilename: true,
    });
  } else if (view === "search") {
    els.viewEyebrow.textContent = "YouTube";
    els.viewTitle.textContent = "Search";
    renderSearchResults(state.searchResults);
  } else if (view === "playlist") {
    const pl = state.playlists.find((p) => p.id === playlistId);
    els.viewEyebrow.textContent = "Playlist";
    els.viewTitle.textContent = pl?.name || "Playlist";
    const editBtn = document.createElement("button");
    editBtn.type = "button";
    editBtn.className = "btn secondary compact";
    editBtn.textContent = "Edit";
    editBtn.onclick = () => setView("editor", playlistId);
    els.viewActions.appendChild(editBtn);
    await refreshLibrary();
    const byFile = Object.fromEntries(state.library.map((t) => [t.filename, t]));
    const tracks = (pl?.tracks || []).map(
      (fn) =>
        byFile[fn] || {
          filename: fn,
          title: fn,
          channel: "Missing file",
        }
    );
    state.tracks = tracks.filter((t) => byFile[t.filename]);
    renderTrackList(tracks, {
      empty: "Playlist is empty. Add tracks from Library.",
      onPrimary: (t) => {
        if (!byFile[t.filename]) {
          ui.showToast("File missing from library");
          return;
        }
        playLocal(t, state.tracks);
      },
      actionsFor: (t) => [
        ...libraryActions(t),
        {
          title: "Remove from playlist",
          icon: trashIcon(),
          danger: true,
          action: async () => {
            await api.removeFromPlaylist(playlistId, t.filename);
            await refreshPlaylists();
            setView("playlist", playlistId);
          },
        },
      ],
    });
  } else if (view === "editor") {
    els.viewEyebrow.textContent = "Editor";
    els.viewTitle.textContent = "Playlist editor";
    els.trackList.classList.add("hidden");
    await renderEditor(playlistId);
  } else if (view === "settings") {
    els.viewEyebrow.textContent = "System";
    els.viewTitle.textContent = "Settings";
    els.trackList.classList.add("hidden");
    await renderSettings();
  }
}

function trashIcon() {
  return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M5 7h14M10 11v6M14 11v6M8 7l1-2h6l1 2M7 7l1 12h8l1-12" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>`;
}

function plusIcon() {
  return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>`;
}

function libraryActions(track) {
  return [
    {
      title: "Add to playlist",
      icon: plusIcon(),
      action: async () => {
        if (!state.playlists.length) {
          ui.showToast("Create a playlist first");
          return;
        }
        const choices = state.playlists
          .map(
            (p) =>
              `<option value="${escapeHtml(p.id)}">${escapeHtml(p.name)}</option>`
          )
          .join("");
        let selected = state.playlists[0].id;
        await showModal(
          "Add to playlist",
          `<div class="field"><label>Playlist</label><select id="pl-pick" style="width:100%;padding:10px;border-radius:10px;background:#0c0d10;color:#fff;border:1px solid rgba(255,255,255,.14)">${choices}</select></div>`,
          async () => {
            selected = document.getElementById("pl-pick").value;
            await api.addToPlaylist(selected, track.filename);
            ui.showToast("Added to playlist");
            await refreshPlaylists();
            return true;
          }
        );
      },
    },
    {
      title: "Delete file",
      icon: trashIcon(),
      danger: true,
      action: async () => {
        const ok = await showModal(
          "Delete file?",
          `<p>Permanently delete <strong>${escapeHtml(track.filename)}</strong> from disk?</p>`
        );
        if (!ok) return;
        await api.deleteFile(track.filename);
        ui.showToast("Deleted");
        await refreshLibrary();
        await refreshPlaylists();
        setView(state.view, state.playlistId);
      },
    },
  ];
}

function renderTrackList(tracks, { empty, onPrimary, actionsFor, showFilename } = {}) {
  els.trackList.innerHTML = "";
  if (!tracks.length) {
    els.emptyCopy.textContent = empty || "Nothing here.";
    els.emptyState.classList.remove("hidden");
    els.emptyState.setAttribute("aria-hidden", "false");
    return;
  }
  els.emptyState.classList.add("hidden");
  els.emptyState.setAttribute("aria-hidden", "true");
  const frag = document.createDocumentFragment();
  tracks.forEach((track, i) => {
    const row = trackRowEl(
      showFilename ? { ...track, channel: track.filename } : track,
      {
        onPrimary,
        actions: actionsFor?.(track) || [],
      }
    );
    row.dataset.filename = track.filename || "";
    frag.appendChild(row);
    if (!reduceMotion && typeof gsap !== "undefined" && state.view === "search") {
      gsap.from(row, {
        autoAlpha: 0,
        y: 8,
        duration: 0.22,
        delay: Math.min(i * 0.04, 0.4),
        ease: "power2.out",
      });
    }
  });
  els.trackList.appendChild(frag);
}

function renderSearchResults(results) {
  state.tracks = [];
  els.trackList.innerHTML = "";
  if (!results.length) {
    els.emptyCopy.textContent = "Search YouTube. Click a result to download the MP3.";
    els.emptyState.classList.remove("hidden");
    return;
  }
  els.emptyState.classList.add("hidden");
  results.forEach((item, i) => {
    const job = state.downloadJobs[item.video_id];
    const row = trackRowEl(item, {
      badge: item.downloaded
        ? { text: "Already downloaded" }
        : job?.status === "downloading" || job?.status === "queued"
          ? { text: `Downloading ${Math.round(job.progress || 0)}%`, warn: true }
          : null,
      progress: job && job.status !== "ready" ? job.progress : null,
      onPrimary: () => onSearchClick(item),
      actions: [],
    });
    row.dataset.videoId = item.video_id;
    els.trackList.appendChild(row);
    if (!reduceMotion && typeof gsap !== "undefined") {
      gsap.from(row, {
        autoAlpha: 0,
        y: 8,
        duration: 0.22,
        delay: Math.min(i * 0.04, 0.4),
        ease: "power2.out",
      });
    }
  });
}

async function onSearchClick(item) {
  if (item.downloaded && item.filename) {
    const track =
      state.library.find((t) => t.filename === item.filename) || {
        filename: item.filename,
        title: item.title,
        channel: item.channel,
        cover: item.cover,
        cover_url: item.cover_url,
        duration: item.duration,
      };
    await refreshLibrary();
    await playLocal(track, state.library);
    return;
  }
  // Prevent multiple concurrent downloads from the same row click.
  const active = state.downloadJobs[item.video_id];
  if (active && active.status !== "ready") {
    ui.showToast("Sedang download…");
    return;
  }
  try {
    const job = await api.startDownload({
      url: item.url,
      video_id: item.video_id,
      title: item.title,
      channel: item.channel,
      duration: item.duration,
    });
    if (job.status === "already_downloaded") {
      item.downloaded = true;
      item.filename = job.filename;
      await refreshLibrary();
      renderSearchResults(state.searchResults.map((r) =>
        r.video_id === item.video_id
          ? { ...r, downloaded: true, filename: job.filename }
          : r
      ));
      ui.showToast("Already in library");
      return;
    }
    state.downloadJobs[item.video_id] = job;
    renderSearchResults(state.searchResults);
    ui.showToast(`Downloading: ${item.title}`);
    // Throttle UI updates to reduce progress flicker.
    let lastUi = 0;
    const done = await pollDownload(job.job_id, (status) => {
      state.downloadJobs[item.video_id] = status;
      const now = Date.now();
      if (now - lastUi < 450) return;
      lastUi = now;
      renderSearchResults(state.searchResults);
    });
    item.downloaded = true;
    item.filename = done.filename;
    delete state.downloadJobs[item.video_id];
    state.searchResults = state.searchResults.map((r) =>
      r.video_id === item.video_id
        ? { ...r, downloaded: true, filename: done.filename, cover: done.cover }
        : r
    );
    await refreshLibrary();
    renderSearchResults(state.searchResults);
    ui.showToast(`Saved: ${done.filename}`);
  } catch (err) {
    delete state.downloadJobs[item.video_id];
    renderSearchResults(state.searchResults);
    ui.showToast(String(err.message || err));
  }
}

async function runSearch(e) {
  e?.preventDefault();
  const q = els.searchInput.value.trim();
  if (!q) return;
  if (state.view !== "search") await setView("search");
  ui.showToast("Searching…");
  try {
    state.searchResults = await api.search(q);
    renderSearchResults(state.searchResults);
    ui.showToast("");
  } catch (err) {
    ui.showToast(String(err.message || err));
  }
}

async function renderSettings() {
  await refreshSettings();
  els.settingsPanel.classList.remove("hidden");
  const version = state.settings.version || "—";
  els.settingsPanel.innerHTML = `
    <div class="field">
      <label for="setting-dir">Download folder</label>
      <input id="setting-dir" type="text" value="${escapeHtml(state.settings.download_dir)}">
      <p class="field-hint">Library, Explorer, and playlists.json always use this folder.</p>
    </div>
    <div class="editor-toolbar">
      <button type="button" class="btn primary" id="btn-save-settings">Apply</button>
    </div>
    <div class="settings-section">
      <div class="section-label">Updates</div>
      <div class="update-card panel inset">
        <div class="update-row">
          <span class="field-hint">Installed version</span>
          <span class="mono" id="setting-version">${escapeHtml(version)}</span>
        </div>
        <div id="update-status" class="update-status" hidden></div>
        <div class="editor-toolbar">
          <button type="button" class="btn secondary" id="btn-check-update">Check for updates</button>
          <button type="button" class="btn primary hidden" id="btn-install-update">Install update</button>
        </div>
      </div>
    </div>
  `;
  document.getElementById("btn-save-settings").onclick = async () => {
    const dir = document.getElementById("setting-dir").value.trim();
    if (!dir) return;
    try {
      state.settings = await api.updateSettings(dir);
      await refreshLibrary();
      await refreshPlaylists();
      ui.showToast("Download folder updated");
      els.pathChip.textContent = state.settings.download_dir;
      els.pathChip.title = state.settings.download_dir;
    } catch (err) {
      ui.showToast(String(err.message || err));
    }
  };

  const statusEl = document.getElementById("update-status");
  const installBtn = document.getElementById("btn-install-update");
  const checkBtn = document.getElementById("btn-check-update");

  function showUpdateStatus(info) {
    statusEl.hidden = false;
    if (info.error) {
      statusEl.innerHTML = `<p class="field-error">${escapeHtml(info.error)}</p>`;
      installBtn.classList.add("hidden");
      return;
    }
    if (info.update_available) {
      statusEl.innerHTML = `<p class="update-available">Update available: <strong>${escapeHtml(info.local_version)}</strong> → <strong>${escapeHtml(info.remote_version)}</strong></p>`;
      installBtn.classList.remove("hidden");
      return;
    }
    statusEl.innerHTML = `<p class="field-hint">You are on the latest version (${escapeHtml(info.local_version)}).</p>`;
    installBtn.classList.add("hidden");
  }

  checkBtn.onclick = async () => {
    checkBtn.disabled = true;
    checkBtn.textContent = "Checking…";
    try {
      const info = await api.checkUpdate();
      showUpdateStatus(info);
      if (info.remote_version) {
        document.getElementById("setting-version").textContent = info.local_version;
      }
    } catch (err) {
      showUpdateStatus({ error: String(err.message || err) });
    } finally {
      checkBtn.disabled = false;
      checkBtn.textContent = "Check for updates";
    }
  };

  installBtn.onclick = async () => {
    installBtn.disabled = true;
    checkBtn.disabled = true;
    installBtn.textContent = "Installing…";
    try {
      const result = await api.installUpdate();
      showUpdateStatus({
        ...result,
        update_available: false,
        error: null,
      });
      if (result.updated) {
        statusEl.innerHTML = `<p class="update-available">${escapeHtml(result.message || "Update installed")}</p>`;
        installBtn.classList.add("hidden");
        if (result.remote_version) {
          document.getElementById("setting-version").textContent = result.remote_version;
          state.settings.version = result.remote_version;
        }
        ui.showToast("Update installed — restart JJMP3");
      }
    } catch (err) {
      showUpdateStatus({ error: String(err.message || err) });
    } finally {
      installBtn.disabled = false;
      checkBtn.disabled = false;
      installBtn.textContent = "Install update";
    }
  };
}

async function renderEditor(playlistId) {
  await refreshLibrary();
  await refreshPlaylists();
  const pl = state.playlists.find((p) => p.id === playlistId) || state.playlists[0];
  if (!pl) {
    els.editorPanel.classList.remove("hidden");
    els.editorPanel.innerHTML = `<p class="field-hint">Create a playlist first.</p>`;
    return;
  }
  state.playlistId = pl.id;
  const doc = await api.playlistDocument();
  els.editorPanel.classList.remove("hidden");
  els.editorPanel.innerHTML = `
    <div class="editor-toolbar">
      <div class="field" style="flex:1;min-width:180px;margin:0">
        <label for="editor-name">Name</label>
        <input id="editor-name" type="text" value="${escapeHtml(pl.name)}">
      </div>
      <button type="button" class="btn secondary" id="btn-save-visual">Save playlist</button>
      <button type="button" class="btn danger" id="btn-delete-pl">Delete</button>
    </div>
    <div>
      <div class="section-label">Tracks</div>
      <div id="editor-tracks" class="editor-tracks"></div>
      <div class="field" style="margin-top:12px">
        <label for="add-track-select">Add from library</label>
        <div class="editor-toolbar">
          <select id="add-track-select" style="flex:1;padding:10px;border-radius:10px;background:#0c0d10;color:#fff;border:1px solid rgba(255,255,255,.14)">
            ${state.library
              .map(
                (t) =>
                  `<option value="${escapeHtml(t.filename)}">${escapeHtml(t.title)}</option>`
              )
              .join("")}
          </select>
          <button type="button" class="btn secondary" id="btn-add-track">Add</button>
        </div>
      </div>
    </div>
    <div class="field">
      <label for="json-editor">playlists.json</label>
      <textarea id="json-editor" spellcheck="false">${escapeHtml(JSON.stringify(doc, null, 2))}</textarea>
      <p id="json-error" class="field-error" hidden></p>
      <div class="editor-toolbar" style="margin-top:8px">
        <button type="button" class="btn primary" id="btn-save-json">Save JSON</button>
      </div>
    </div>
  `;

  const tracksEl = document.getElementById("editor-tracks");
  let tracks = [...pl.tracks];

  function paintTracks() {
    tracksEl.innerHTML = "";
    tracks.forEach((fn, i) => {
      const row = document.createElement("div");
      row.className = "editor-track";
      row.draggable = true;
      row.innerHTML = `<span class="handle">${i + 1}</span><span>${escapeHtml(fn)}</span>
        <button type="button" class="icon-btn" title="Remove">${trashIcon()}</button>`;
      row.querySelector("button").onclick = () => {
        tracks = tracks.filter((t) => t !== fn);
        paintTracks();
      };
      row.addEventListener("dragstart", () => {
        row.dataset.dragging = "1";
      });
      row.addEventListener("dragend", () => {
        delete row.dataset.dragging;
      });
      row.addEventListener("dragover", (e) => e.preventDefault());
      row.addEventListener("drop", (e) => {
        e.preventDefault();
        const from = [...tracksEl.children].findIndex((c) => c.dataset.dragging === "1");
        const to = i;
        if (from < 0 || from === to) return;
        const [moved] = tracks.splice(from, 1);
        tracks.splice(to, 0, moved);
        paintTracks();
      });
      tracksEl.appendChild(row);
    });
  }
  paintTracks();

  document.getElementById("btn-add-track").onclick = () => {
    const sel = document.getElementById("add-track-select");
    if (!sel.value) return;
    if (!tracks.includes(sel.value)) tracks.push(sel.value);
    paintTracks();
  };

  document.getElementById("btn-save-visual").onclick = async () => {
    const name = document.getElementById("editor-name").value.trim();
    if (!name) return;
    await api.renamePlaylist(pl.id, name);
    await api.setPlaylistTracks(pl.id, tracks);
    await refreshPlaylists();
    ui.showToast("Playlist saved");
    const fresh = await api.playlistDocument();
    document.getElementById("json-editor").value = JSON.stringify(fresh, null, 2);
  };

  document.getElementById("btn-delete-pl").onclick = async () => {
    const ok = await showModal("Delete playlist?", `<p>Remove this playlist from JSON?</p>`);
    if (!ok) return;
    await api.deletePlaylist(pl.id);
    await refreshPlaylists();
    setView("library");
  };

  document.getElementById("btn-save-json").onclick = async () => {
    const errEl = document.getElementById("json-error");
    errEl.hidden = true;
    let parsed;
    try {
      parsed = JSON.parse(document.getElementById("json-editor").value);
    } catch (err) {
      errEl.textContent = String(err.message || err);
      errEl.hidden = false;
      return;
    }
    try {
      const saved = await api.savePlaylistDocument(parsed);
      document.getElementById("json-editor").value = JSON.stringify(saved, null, 2);
      await refreshPlaylists();
      ui.showToast("JSON saved");
    } catch (err) {
      errEl.textContent = String(err.message || err);
      errEl.hidden = false;
    }
  };
}

function wireControls() {
  document.querySelectorAll(".nav-item[data-view]").forEach((btn) => {
    btn.addEventListener("click", () => setView(btn.dataset.view));
  });
  document.getElementById("btn-new-playlist").onclick = async () => {
    let name = "";
    await showModal(
      "New playlist",
      `<div class="field"><label>Name</label><input id="new-pl-name" type="text" placeholder="Late night"></div>`,
      async () => {
        name = document.getElementById("new-pl-name").value.trim();
        if (!name) return false;
        const pl = await api.createPlaylist(name);
        await refreshPlaylists();
        setView("playlist", pl.id);
        return true;
      }
    );
  };
  els.searchForm.addEventListener("submit", runSearch);
  document.getElementById("btn-play").onclick = () => player.togglePlay();
  document.getElementById("btn-prev").onclick = () => player.prev();
  document.getElementById("btn-next").onclick = () => player.next();
  document.getElementById("btn-shuffle").onclick = (e) => {
    const on = player.toggleShuffle();
    e.currentTarget.setAttribute("aria-pressed", String(on));
  };
  document.getElementById("btn-repeat").onclick = (e) => {
    const mode = player.cycleRepeat();
    e.currentTarget.dataset.mode = mode;
  };
  document.getElementById("seek-bar").addEventListener("input", (e) => {
    player.seek(Number(e.target.value) / 100);
  });
  document.getElementById("volume-bar").addEventListener("input", (e) => {
    player.setVolume(Number(e.target.value) / 100);
  });

  // Keyboard: no animation — instant transport only when not typing
  window.addEventListener("keydown", (e) => {
    const tag = document.activeElement?.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    if (e.code === "Space") {
      e.preventDefault();
      player.togglePlay();
    } else if (e.code === "ArrowRight") {
      player.next();
    } else if (e.code === "ArrowLeft") {
      player.prev();
    }
  });
}

function wireLifecycle() {
  const tabId = crypto.randomUUID();
  const body = () => JSON.stringify({ tab_id: tabId });

  const ping = () => {
    fetch("/api/lifecycle/ping", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body(),
      keepalive: true,
    }).catch(() => {});
  };

  ping();
  const timer = setInterval(ping, 4000);

  const quit = () => {
    clearInterval(timer);
    if (navigator.sendBeacon) {
      navigator.sendBeacon(
        "/api/lifecycle/quit",
        new Blob([body()], { type: "application/json" })
      );
    } else {
      fetch("/api/lifecycle/quit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: body(),
        keepalive: true,
      }).catch(() => {});
    }
  };

  window.addEventListener("pagehide", quit);
  window.addEventListener("beforeunload", quit);
}

async function boot() {
  wireControls();
  wireLifecycle();
  try {
    await refreshSettings();
    await refreshLibrary();
    await refreshPlaylists();
    await setView("library");
  } catch (err) {
    ui.showToast(String(err.message || err));
  }
  runIntro();
}

boot();
