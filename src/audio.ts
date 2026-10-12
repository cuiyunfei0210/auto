import type { Song } from "./songs";

export type PlayerSnap = {
  songId: string | null;
  phrase: number;
  playing: boolean;
  beat: number;
};

type Listener = (snap: PlayerSnap) => void;

type FlatNote = {
  phrase: number;
  midi: number | null;
  beats: number;
};

const STORAGE_KEY = "yaya-volume";

function readVolume(): number {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return 0.85;
    const value = Number(raw);
    if (Number.isFinite(value) && value >= 0 && value <= 1) return value;
  } catch {
    /* private mode */
  }
  return 0.85;
}

function flatten(song: Song): FlatNote[] {
  const notes: FlatNote[] = [];
  song.phrases.forEach((phrase, phraseIndex) => {
    for (const note of phrase.notes) {
      notes.push({ phrase: phraseIndex, midi: note.midi, beats: note.beats });
    }
  });
  return notes;
}

export class MelodyPlayer {
  private ctx: AudioContext | null = null;
  private master: GainNode | null = null;
  private volume = readVolume();
  private listeners = new Set<Listener>();
  private snap: PlayerSnap = { songId: null, phrase: 0, playing: false, beat: 0 };
  private timer = 0;
  private pending: number[] = [];
  private token = 0;
  private notes: FlatNote[] = [];
  private index = 0;
  private nextTime = 0;
  private bpm = 100;
  private songId: string | null = null;

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    listener(this.snap);
    return () => this.listeners.delete(listener);
  }

  getVolume(): number {
    return this.volume;
  }

  getSnap(): PlayerSnap {
    return this.snap;
  }

  async setVolume(volume: number): Promise<void> {
    this.volume = Math.min(1, Math.max(0, volume));
    try {
      localStorage.setItem(STORAGE_KEY, String(this.volume));
    } catch {
      /* ignore */
    }
    if (this.ctx && this.master) {
      this.master.gain.setValueAtTime(this.volume, this.ctx.currentTime);
    }
  }

  async unlock(): Promise<void> {
    const ctx = await this.ensure();
    if (ctx.state === "suspended") await ctx.resume();
  }

  async play(song: Song): Promise<void> {
    const ctx = await this.ensure();
    if (ctx.state === "suspended") await ctx.resume();
    this.stopRain();
    this.token += 1;
    this.clearPending();
    window.clearInterval(this.timer);
    this.cutNotes();
    this.songId = song.id;
    this.notes = flatten(song);
    this.bpm = song.bpm;
    this.index = 0;
    this.nextTime = ctx.currentTime + 0.08;
    this.emit({ songId: song.id, phrase: 0, playing: true, beat: 0 });
    this.arm();
  }

  async toggle(): Promise<void> {
    if (!this.ctx || !this.songId) return;
    if (this.snap.playing) {
      this.token += 1;
      this.clearPending();
      window.clearInterval(this.timer);
      this.timer = 0;
      this.cutNotes();
      this.emit({ playing: false });
      return;
    }
    if (this.ctx.state === "suspended") await this.ctx.resume();
    this.nextTime = this.ctx.currentTime + 0.06;
    this.runningGain();
    this.emit({ playing: true });
    this.arm();
  }

  stop(): void {
    this.token += 1;
    this.clearPending();
    window.clearInterval(this.timer);
    this.timer = 0;
    this.songId = null;
    this.notes = [];
    this.index = 0;
    this.stopRain();
    if (this.ctx?.state === "suspended") void this.ctx.resume();
    this.cutNotes();
    this.emit({ songId: null, phrase: 0, playing: false, beat: 0 });
  }

  private cutNotes(): void {
    if (!this.ctx || !this.master) return;
    const time = this.ctx.currentTime;
    this.master.gain.cancelScheduledValues(time);
    this.master.gain.setValueAtTime(0.0001, time);
    const next = this.ctx.createGain();
    next.gain.value = this.volume;
    next.connect(this.ctx.destination);
    this.master = next;
  }

  async bell(midi: number, beats = 1): Promise<void> {
    const ctx = await this.ensure();
    if (ctx.state === "suspended") await ctx.resume();
    this.runningGain();
    this.tone(midi, ctx.currentTime, (60 / 120) * beats);
  }

  async animal(kind: AnimalId): Promise<void> {
    const ctx = await this.ensure();
    if (ctx.state === "suspended") await ctx.resume();
    this.runningGain();
    const now = ctx.currentTime;
    if (kind === "cat") this.slide(780, 420, now, 0.35, "triangle");
    if (kind === "dog") {
      this.noise(now, 0.08, 180);
      this.noise(now + 0.14, 0.08, 160);
      this.noise(now + 0.3, 0.12, 140);
    }
    if (kind === "duck") {
      this.blip(520, now, 0.09, "square");
      this.blip(430, now + 0.12, 0.1, "square");
    }
    if (kind === "cow") this.slide(196, 120, now, 0.55, "sawtooth");
    if (kind === "frog") {
      this.blip(420, now, 0.08, "square");
      this.blip(300, now + 0.12, 0.1, "square");
    }
    if (kind === "bird") {
      this.blip(1480, now, 0.06, "sine");
      this.blip(1760, now + 0.08, 0.07, "sine");
      this.blip(1320, now + 0.18, 0.08, "sine");
    }
    if (kind === "sheep") this.slide(480, 360, now, 0.45, "triangle");
    if (kind === "tiger") this.noise(now, 0.35, 90);
  }

  async chime(): Promise<void> {
    const ctx = await this.ensure();
    if (ctx.state === "suspended") await ctx.resume();
    this.runningGain();
    const now = ctx.currentTime;
    [72, 76, 79].forEach((midi, index) => this.tone(midi, now + index * 0.08, 0.25));
  }

  async pop(): Promise<void> {
    const ctx = await this.ensure();
    if (ctx.state === "suspended") await ctx.resume();
    this.runningGain();
    this.blip(880, ctx.currentTime, 0.07, "sine");
  }

  async whistle(): Promise<void> {
    const ctx = await this.ensure();
    if (ctx.state === "suspended") await ctx.resume();
    this.runningGain();
    const now = ctx.currentTime;
    this.slide(700, 980, now, 0.18, "sine");
    this.slide(980, 760, now + 0.18, 0.22, "sine");
  }

  async setRain(on: boolean): Promise<void> {
    const ctx = await this.ensure();
    if (!on) {
      this.stopRain();
      return;
    }
    if (this.rainSource) return;
    if (ctx.state === "suspended") await ctx.resume();
    const buffer = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < data.length; i += 1) data[i] = Math.random() * 2 - 1;
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.loop = true;
    const filter = ctx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.value = 900;
    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0.0001, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.18, ctx.currentTime + 0.4);
    source.connect(filter);
    filter.connect(gain);
    gain.connect(this.master!);
    source.start();
    this.rainSource = source;
    this.rainGain = gain;
  }

  private rainSource: AudioBufferSourceNode | null = null;
  private rainGain: GainNode | null = null;

  private stopRain(): void {
    if (!this.ctx || !this.rainGain || !this.rainSource) {
      this.rainSource = null;
      this.rainGain = null;
      return;
    }
    const time = this.ctx.currentTime;
    this.rainGain.gain.cancelScheduledValues(time);
    this.rainGain.gain.setValueAtTime(Math.max(this.rainGain.gain.value, 0.0001), time);
    this.rainGain.gain.exponentialRampToValueAtTime(0.0001, time + 0.2);
    const source = this.rainSource;
    window.setTimeout(() => {
      try {
        source.stop();
      } catch {
        /* already stopped */
      }
    }, 220);
    this.rainSource = null;
    this.rainGain = null;
  }

  private emit(partial: Partial<PlayerSnap>): void {
    this.snap = { ...this.snap, ...partial };
    for (const listener of this.listeners) listener(this.snap);
  }

  private async ensure(): Promise<AudioContext> {
    if (!this.ctx) {
      const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      this.ctx = new Ctx();
      this.master = this.ctx.createGain();
      this.master.gain.value = this.volume;
      this.master.connect(this.ctx.destination);
    }
    return this.ctx;
  }

  private runningGain(): void {
    if (!this.ctx || !this.master) return;
    const time = this.ctx.currentTime;
    this.master.gain.cancelScheduledValues(time);
    this.master.gain.setValueAtTime(this.volume, time);
  }

  private arm(): void {
    window.clearInterval(this.timer);
    this.tick();
    this.timer = window.setInterval(() => this.tick(), 25);
  }

  private tick(): void {
    if (!this.ctx || !this.snap.playing || this.notes.length === 0) return;
    const horizon = this.ctx.currentTime + 0.16;
    const beat = 60 / this.bpm;
    while (this.nextTime < horizon) {
      const note = this.notes[this.index % this.notes.length];
      const when = this.nextTime;
      const duration = Math.min(note.beats * beat * 0.92, 0.7);
      if (note.midi != null) this.tone(note.midi, when, Math.max(0.08, duration));
      const token = this.token;
      const phrase = note.phrase;
      const looped = this.index > 0 && this.index % this.notes.length === 0;
      const delay = Math.max(0, (when - this.ctx.currentTime) * 1000);
      const timeout = window.setTimeout(() => {
        if (token !== this.token) return;
        this.emit({
          songId: this.songId,
          phrase: looped ? 0 : phrase,
          playing: true,
          beat: this.snap.beat + 1,
        });
      }, delay);
      this.pending.push(timeout);
      this.nextTime += note.beats * beat;
      this.index += 1;
    }
  }

  private clearPending(): void {
    for (const timeout of this.pending) window.clearTimeout(timeout);
    this.pending = [];
  }

  private tone(midi: number, time: number, duration: number): void {
    if (!this.ctx || !this.master) return;
    const freq = 440 * 2 ** ((midi - 69) / 12);
    const gain = this.ctx.createGain();
    gain.gain.setValueAtTime(0.0001, time);
    gain.gain.exponentialRampToValueAtTime(0.9, time + 0.015);
    gain.gain.exponentialRampToValueAtTime(0.0001, time + duration);
    gain.connect(this.master);
    const partials = [
      { ratio: 1, level: 0.7 },
      { ratio: 2.01, level: 0.18 },
      { ratio: 3.8, level: 0.06 },
    ];
    for (const partial of partials) {
      const osc = this.ctx.createOscillator();
      osc.type = "sine";
      osc.frequency.setValueAtTime(freq * partial.ratio, time);
      const partialGain = this.ctx.createGain();
      partialGain.gain.value = partial.level;
      osc.connect(partialGain);
      partialGain.connect(gain);
      osc.start(time);
      osc.stop(time + duration + 0.02);
    }
  }

  private blip(
    freq: number,
    time: number,
    duration: number,
    type: OscillatorType,
  ): void {
    if (!this.ctx || !this.master) return;
    const osc = this.ctx.createOscillator();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, time);
    const gain = this.ctx.createGain();
    gain.gain.setValueAtTime(0.0001, time);
    gain.gain.exponentialRampToValueAtTime(type === "square" || type === "sawtooth" ? 0.18 : 0.35, time + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, time + duration);
    osc.connect(gain);
    gain.connect(this.master);
    osc.start(time);
    osc.stop(time + duration + 0.02);
  }

  private slide(
    from: number,
    to: number,
    time: number,
    duration: number,
    type: OscillatorType,
  ): void {
    if (!this.ctx || !this.master) return;
    const osc = this.ctx.createOscillator();
    osc.type = type;
    osc.frequency.setValueAtTime(from, time);
    osc.frequency.exponentialRampToValueAtTime(Math.max(40, to), time + duration);
    const gain = this.ctx.createGain();
    const level = type === "sawtooth" ? 0.16 : 0.28;
    gain.gain.setValueAtTime(0.0001, time);
    gain.gain.exponentialRampToValueAtTime(level, time + 0.04);
    gain.gain.exponentialRampToValueAtTime(0.0001, time + duration);
    osc.connect(gain);
    gain.connect(this.master);
    osc.start(time);
    osc.stop(time + duration + 0.02);
  }

  private noise(time: number, duration: number, freq: number): void {
    if (!this.ctx || !this.master) return;
    const length = Math.floor(this.ctx.sampleRate * duration);
    const buffer = this.ctx.createBuffer(1, length, this.ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < length; i += 1) data[i] = Math.random() * 2 - 1;
    const source = this.ctx.createBufferSource();
    source.buffer = buffer;
    const filter = this.ctx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.setValueAtTime(freq, time);
    const gain = this.ctx.createGain();
    gain.gain.setValueAtTime(0.0001, time);
    gain.gain.exponentialRampToValueAtTime(0.45, time + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, time + duration);
    source.connect(filter);
    filter.connect(gain);
    gain.connect(this.master);
    source.start(time);
    source.stop(time + duration);
  }
}

export type AnimalId = "cat" | "dog" | "duck" | "cow" | "frog" | "bird" | "sheep" | "tiger";

let player: MelodyPlayer | null = null;

export function getPlayer(): MelodyPlayer {
  if (!player) player = new MelodyPlayer();
  return player;
}

export function speak(text: string): void {
  if (typeof speechSynthesis === "undefined") return;
  speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "zh-CN";
  utterance.rate = 0.86;
  const voice = speechSynthesis
    .getVoices()
    .find((item) => item.lang.toLowerCase().startsWith("zh"));
  if (voice) utterance.voice = voice;
  speechSynthesis.speak(utterance);
}

export function hush(): void {
  if (typeof speechSynthesis !== "undefined") speechSynthesis.cancel();
}
