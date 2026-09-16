/** API client for JJMP3 local library player. */

async function request(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  let data = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }
  if (!res.ok) {
    const detail = data?.detail || data || res.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export const api = {
  health: () => request("/api/health"),
  search: (q) => request(`/api/search?q=${encodeURIComponent(q)}`),
  library: () => request("/api/library"),
  deleteFile: (filename) =>
    request(`/api/library/file/${encodeURIComponent(filename).replace(/%2F/g, "/")}`, {
      method: "DELETE",
    }),
  fileUrl: (filename) =>
    `/api/library/file/${filename.split("/").map(encodeURIComponent).join("/")}`,
  coverUrl: (cover) =>
    cover ? `/api/library/cover/${cover.split("/").map(encodeURIComponent).join("/")}` : null,
  startDownload: (body) =>
    request("/api/download", { method: "POST", body: JSON.stringify(body) }),
  downloadStatus: (jobId) => request(`/api/download/${jobId}`),
  settings: () => request("/api/settings"),
  updateSettings: (download_dir) =>
    request("/api/settings", {
      method: "PUT",
      body: JSON.stringify({ download_dir }),
    }),
  checkUpdate: () => request("/api/update/check"),
  installUpdate: () => request("/api/update/install", { method: "POST" }),
  playlists: () => request("/api/playlists"),
  playlistDocument: () => request("/api/playlists/document"),
  savePlaylistDocument: (doc) =>
    request("/api/playlists/document", {
      method: "PUT",
      body: JSON.stringify(doc),
    }),
  createPlaylist: (name) =>
    request("/api/playlists", { method: "POST", body: JSON.stringify({ name }) }),
  renamePlaylist: (id, name) =>
    request(`/api/playlists/${id}`, { method: "PUT", body: JSON.stringify({ name }) }),
  deletePlaylist: (id) => request(`/api/playlists/${id}`, { method: "DELETE" }),
  addToPlaylist: (id, filename) =>
    request(`/api/playlists/${id}/tracks`, {
      method: "POST",
      body: JSON.stringify({ filename }),
    }),
  removeFromPlaylist: (id, filename) =>
    request(`/api/playlists/${id}/tracks?filename=${encodeURIComponent(filename)}`, {
      method: "DELETE",
    }),
  setPlaylistTracks: (id, tracks) =>
    request(`/api/playlists/${id}/tracks`, {
      method: "PUT",
      body: JSON.stringify({ tracks }),
    }),
  lifecyclePing: (tabId) =>
    request("/api/lifecycle/ping", {
      method: "POST",
      body: JSON.stringify({ tab_id: tabId }),
    }),
  lifecycleQuit: (tabId) =>
    request("/api/lifecycle/quit", {
      method: "POST",
      body: JSON.stringify({ tab_id: tabId }),
    }),
};

export async function pollDownload(jobId, onProgress, { timeoutMs = 600_000 } = {}) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const job = await api.downloadStatus(jobId);
    if (typeof onProgress === "function") onProgress(job);
    if (job.status === "ready") return job;
    if (job.status === "error") throw new Error(job.error || "Download failed");
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error("Download timed out");
}
