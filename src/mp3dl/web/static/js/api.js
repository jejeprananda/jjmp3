const API = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  if (res.status === 204) return null;
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res.text();
}

export const api = {
  search: (q) => request(`/search?q=${encodeURIComponent(q)}`),
  createTrack: (url) => request("/tracks", { method: "POST", body: JSON.stringify({ url }) }),
  getPlaylists: () => request("/playlists"),
  createPlaylist: (name) => request("/playlists", { method: "POST", body: JSON.stringify({ name }) }),
  renamePlaylist: (id, name) => request(`/playlists/${id}`, { method: "PUT", body: JSON.stringify({ name }) }),
  deletePlaylist: (id) => request(`/playlists/${id}`, { method: "DELETE" }),
  getPlaylistTracks: (id) => request(`/playlists/${id}/tracks`),
  addToPlaylist: (playlistId, trackId) =>
    request(`/playlists/${playlistId}/tracks`, { method: "POST", body: JSON.stringify({ track_id: trackId }) }),
  removeFromPlaylist: (playlistId, trackId) =>
    request(`/playlists/${playlistId}/tracks/${trackId}`, { method: "DELETE" }),
  reorderPlaylist: (playlistId, trackIds) =>
    request(`/playlists/${playlistId}/tracks/reorder`, { method: "PUT", body: JSON.stringify({ track_ids: trackIds }) }),
  getQueue: () => request("/queue"),
  addToQueue: (trackId) => request("/queue", { method: "POST", body: JSON.stringify({ track_id: trackId }) }),
  addPlaylistToQueue: (playlistId) => request("/queue", { method: "POST", body: JSON.stringify({ playlist_id: playlistId }) }),
  removeFromQueue: (queueId) => request(`/queue/${queueId}`, { method: "DELETE" }),
  reorderQueue: (queueIds) => request("/queue/reorder", { method: "PUT", body: JSON.stringify({ queue_ids: queueIds }) }),
  clearQueue: () => request("/queue", { method: "DELETE" }),
  getHistory: () => request("/history"),
  logHistory: (trackId) => request("/history", { method: "POST", body: JSON.stringify({ track_id: trackId }) }),
  streamStatus: (trackId) => request(`/stream/${trackId}/status`),
  download: (trackId) => request(`/download/${trackId}`, { method: "POST" }),
  importYoutubePlaylist: (url, playlistId) =>
    request("/import/youtube-playlist", { method: "POST", body: JSON.stringify({ url, playlist_id: playlistId }) }),
  clearCache: () => request("/cache", { method: "DELETE" }),
};

export async function ensureTrackFromSearch(result) {
  return api.createTrack(result.url);
}

export async function pollUntilReady(trackId, onProgress) {
  for (let i = 0; i < 600; i++) {
    const status = await api.streamStatus(trackId);
    if (status.error) {
      throw new Error(status.error);
    }
    if (onProgress) onProgress(status.progress || 0);
    if (status.ready) return status;
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error("Timeout menunggu audio siap");
}
