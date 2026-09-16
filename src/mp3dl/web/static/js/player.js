import { api } from "./api.js";

export function formatTime(seconds) {
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
    this._audioCtx = null;
    this._analyser = null;
    this._raf = null;
    this._source = null;
    this._reduced =
      typeof matchMedia === "function" &&
      matchMedia("(prefers-reduced-motion: reduce)").matches;

    audioEl.addEventListener("timeupdate", () => this._onTimeUpdate());
    audioEl.addEventListener("ended", () => this._onEnded());
    audioEl.addEventListener("loadedmetadata", () => this._onTimeUpdate());
    audioEl.addEventListener("play", () => {
      this.ui.setPlaying(true);
      this._startViz();
    });
    audioEl.addEventListener("pause", () => {
      this.ui.setPlaying(false);
      this._stopViz();
    });

    document.addEventListener("visibilitychange", () => {
      if (document.hidden) this._stopViz();
      else if (!this.audio.paused) this._startViz();
    });
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
    if (!track?.filename) throw new Error("Track has no local file");
    this.currentTrack = track;
    this.ui.updateNowPlaying(track);
    this.audio.src = api.fileUrl(track.filename);
    await this.audio.play();
  }

  async playAt(index) {
    if (index < 0 || index >= this.queue.length) return;
    this.queueIndex = index;
    await this.playTrack(this.queue[index]);
  }

  async play() {
    if (this.currentTrack && this.audio.src) {
      await this.audio.play();
      return;
    }
    if (this.queue.length) await this.playAt(Math.max(0, this.queueIndex));
  }

  pause() {
    this.audio.pause();
  }

  togglePlay() {
    if (this.audio.paused) return this.play();
    this.pause();
  }

  seek(ratio) {
    if (!Number.isFinite(this.audio.duration)) return;
    this.audio.currentTime = ratio * this.audio.duration;
  }

  async next() {
    if (!this.queue.length) return;
    if (this.shuffle) {
      const remaining = this.queue
        .map((_, i) => i)
        .filter((i) => i !== this.queueIndex && !this.shuffledPlayed.has(i));
      if (!remaining.length) {
        if (this.repeat === "all") {
          this.shuffledPlayed.clear();
          await this.playAt(Math.floor(Math.random() * this.queue.length));
        }
        return;
      }
      this.shuffledPlayed.add(this.queueIndex);
      const pick = remaining[Math.floor(Math.random() * remaining.length)];
      await this.playAt(pick);
      return;
    }
    const next = this.queueIndex + 1;
    if (next < this.queue.length) await this.playAt(next);
    else if (this.repeat === "all") await this.playAt(0);
  }

  async prev() {
    if (this.audio.currentTime > 3) {
      this.audio.currentTime = 0;
      return;
    }
    if (!this.queue.length) return;
    const prev = this.queueIndex - 1;
    if (prev >= 0) await this.playAt(prev);
    else if (this.repeat === "all") await this.playAt(this.queue.length - 1);
  }

  _onTimeUpdate() {
    this.ui.updateProgress(this.audio.currentTime || 0, this.audio.duration || 0);
  }

  async _onEnded() {
    if (this.repeat === "one") {
      this.audio.currentTime = 0;
      await this.audio.play();
      return;
    }
    await this.next();
  }

  _ensureAudioGraph() {
    if (this._reduced || this._analyser) return;
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return;
    try {
      this._audioCtx = new Ctx();
      this._analyser = this._audioCtx.createAnalyser();
      this._analyser.fftSize = 64;
      this._source = this._audioCtx.createMediaElementSource(this.audio);
      this._source.connect(this._analyser);
      this._analyser.connect(this._audioCtx.destination);
    } catch {
      this._analyser = null;
    }
  }

  _startViz() {
    if (this._reduced) return;
    this._ensureAudioGraph();
    if (!this._analyser) return;
    if (this._audioCtx?.state === "suspended") this._audioCtx.resume();
    const canvas = document.getElementById("viz");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const data = new Uint8Array(this._analyser.frequencyBinCount);
    const draw = () => {
      this._raf = requestAnimationFrame(draw);
      this._analyser.getByteFrequencyData(data);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const bars = 8;
      const step = Math.floor(data.length / bars);
      const w = canvas.width / bars;
      for (let i = 0; i < bars; i++) {
        const v = data[i * step] / 255;
        const h = Math.max(2, v * canvas.height);
        ctx.fillStyle = `rgba(232,165,75,${0.25 + v * 0.55})`;
        ctx.fillRect(i * w + 2, canvas.height - h, w - 4, h);
      }
    };
    this._stopViz();
    draw();
  }

  _stopViz() {
    if (this._raf) cancelAnimationFrame(this._raf);
    this._raf = null;
    const canvas = document.getElementById("viz");
    if (canvas) {
      const ctx = canvas.getContext("2d");
      ctx?.clearRect(0, 0, canvas.width, canvas.height);
    }
  }
}
