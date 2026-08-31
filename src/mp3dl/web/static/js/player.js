import { api, pollUntilReady } from "./api.js";

function formatTime(seconds) {
  if (!seconds || !Number.isFinite(seconds)) return "0:00";
  const s = Math.floor(seconds);
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${String(r).padStart(2, "0")}`;
}

export class Player {
  constructor(audioEl, ui) {
    this.audio = audioEl;
    this.ui = ui;
    this.queue = [];
    this.queueIndex = -1;
    this.currentTrack = null;
    this.shuffle = false;
    this.repeat = "off";
    this.shuffledPlayed = new Set();
    this._loggedCurrent = false;

    audioEl.addEventListener("timeupdate", () => this._onTimeUpdate());
    audioEl.addEventListener("ended", () => this._onEnded());
    audioEl.addEventListener("loadedmetadata", () => this._onTimeUpdate());
  }

  setVolume(v) {
    this.audio.volume = Math.max(0, Math.min(1, v));
  }

  toggleShuffle() {
    this.shuffle = !this.shuffle;
    this.shuffledPlayed.clear();
    return this.shuffle;
  }

  cycleRepeat() {
    const order = ["off", "all", "one"];
    const idx = order.indexOf(this.repeat);
    this.repeat = order[(idx + 1) % order.length];
    return this.repeat;
  }

  setQueue(tracks, startIndex = 0) {
    this.queue = tracks.slice();
    this.queueIndex = startIndex;
    this.shuffledPlayed.clear();
  }

  async playTrack(track) {
    this.currentTrack = track;
    this._loggedCurrent = false;
    this.ui.updateNowPlaying(track);
    this.ui.showToast(`Memuat: ${track.title}…`);

    try {
      await pollUntilReady(track.id, (pct) => {
        this.ui.showToast(`Buffering ${Math.round(pct)}%…`);
      });
    } catch (err) {
      this.ui.showToast(String(err.message || err));
      throw err;
    }

    this.audio.src = `/api/stream/${track.id}`;
    await this.audio.play();
    this.ui.setPlaying(true);
    this.ui.showToast("");
  }

  async playAt(index) {
    if (index < 0 || index >= this.queue.length) return;
    this.queueIndex = index;
    await this.playTrack(this.queue[index]);
  }

  async play() {
    if (this.currentTrack && this.audio.src) {
      await this.audio.play();
      this.ui.setPlaying(true);
      return;
    }
    if (this.queue.length) {
      const idx = this.queueIndex >= 0 ? this.queueIndex : 0;
      await this.playAt(idx);
    }
  }

  pause() {
    this.audio.pause();
    this.ui.setPlaying(false);
  }

  togglePlay() {
    if (this.audio.paused) return this.play();
    this.pause();
  }

  async playNext() {
    if (!this.queue.length) return;
    if (this.repeat === "one" && this.currentTrack) {
      this.audio.currentTime = 0;
      await this.audio.play();
      return;
    }
    let next = this.queueIndex + 1;
    if (this.shuffle) {
      next = this._nextShuffleIndex();
    } else if (next >= this.queue.length) {
      if (this.repeat === "all") next = 0;
      else return this.pause();
    }
    await this.playAt(next);
  }

  async playPrev() {
    if (this.audio.currentTime > 3) {
      this.audio.currentTime = 0;
      return;
    }
    if (this.queueIndex > 0) {
      await this.playAt(this.queueIndex - 1);
    }
  }

  _nextShuffleIndex() {
    const unplayed = this.queue
      .map((_, i) => i)
      .filter((i) => !this.shuffledPlayed.has(i) && i !== this.queueIndex);
    if (!unplayed.length) {
      this.shuffledPlayed.clear();
      if (this.repeat !== "all") return this.queueIndex;
      return Math.floor(Math.random() * this.queue.length);
    }
    const pick = unplayed[Math.floor(Math.random() * unplayed.length)];
    this.shuffledPlayed.add(this.queueIndex);
    return pick;
  }

  seek(ratio) {
    if (this.audio.duration) {
      this.audio.currentTime = this.audio.duration * ratio;
    }
  }

  async _onEnded() {
    if (this.currentTrack && !this._loggedCurrent) {
      await api.logHistory(this.currentTrack.id);
      this._loggedCurrent = true;
    }
    await this.playNext();
  }

  _onTimeUpdate() {
    const cur = this.audio.currentTime || 0;
    const dur = this.audio.duration || 0;
    this.ui.updateProgress(cur, dur);
  }
}

export { formatTime };
