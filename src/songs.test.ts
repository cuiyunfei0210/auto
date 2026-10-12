import assert from "node:assert/strict";
import { songSeconds, songs } from "./songs.ts";

const ids = new Set<string>();

for (const song of songs) {
  assert.equal(ids.has(song.id), false, `duplicate id ${song.id}`);
  ids.add(song.id);
  assert.ok(song.title.length > 0, song.id);
  assert.ok(song.phrases.length >= 3, song.id);
  let beats = 0;
  for (const phrase of song.phrases) {
    assert.ok(phrase.lyric.trim().length > 0, song.id);
    assert.ok(phrase.notes.length > 0, `${song.id} empty phrase`);
    for (const note of phrase.notes) {
      assert.ok(note.beats > 0 && note.beats <= 4, `${song.id} beats`);
      if (note.midi != null) {
        assert.ok(note.midi >= 48 && note.midi <= 84, `${song.id} midi ${note.midi}`);
      }
      beats += note.beats;
    }
  }
  const seconds = songSeconds(song);
  assert.ok(seconds >= 8 && seconds <= 90, `${song.id} is ${seconds}s`);
  assert.ok(Math.abs(seconds - Math.round((beats * 60) / song.bpm)) <= 1);
}

assert.equal(songs.length, 11);
console.log(`ok ${songs.length} songs`);
