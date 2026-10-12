export type Note = {
  midi: number | null;
  beats: number;
};

export type Phrase = {
  lyric: string;
  notes: Note[];
};

export type Song = {
  id: string;
  title: string;
  emoji: string;
  credit: string;
  color: string;
  ink: string;
  bpm: number;
  phrases: Phrase[];
};

const SCALE = [0, 2, 4, 5, 7, 9, 11];

/** Scale degree 1–7 in C major. Octave 0 is the C4 octave. */
function d(degree: number, beats = 1, octave = 0): Note {
  return { midi: 60 + SCALE[degree - 1] + octave * 12, beats };
}

function line(lyric: string, notes: Note[]): Phrase {
  return { lyric, notes };
}

export const songs: Song[] = [
  {
    id: "tigers",
    title: "两只老虎",
    emoji: "🐯",
    credit: "传统儿歌 · 音乐盒",
    color: "#ffd36b",
    ink: "#8a4b00",
    bpm: 108,
    phrases: [
      line("两只老虎", [d(1), d(2), d(3), d(1)]),
      line("两只老虎", [d(1), d(2), d(3), d(1)]),
      line("跑得快", [d(3), d(4), d(5, 2)]),
      line("跑得快", [d(3), d(4), d(5, 2)]),
      line("一只没有耳朵", [d(5), d(6), d(5), d(4), d(3), d(1)]),
      line("一只没有尾巴", [d(5), d(6), d(5), d(4), d(3), d(1)]),
      line("真奇怪", [d(1), d(5, 1, -1), d(1, 2)]),
      line("真奇怪", [d(1), d(5, 1, -1), d(1, 2)]),
    ],
  },
  {
    id: "star",
    title: "小星星",
    emoji: "⭐",
    credit: "传统儿歌 · 音乐盒",
    color: "#c9e4ff",
    ink: "#1d4f86",
    bpm: 92,
    phrases: [
      line("一闪一闪亮晶晶", [d(1), d(1), d(5), d(5), d(6), d(6), d(5, 2)]),
      line("满天都是小星星", [d(4), d(4), d(3), d(3), d(2), d(2), d(1, 2)]),
      line("挂在天上放光明", [d(5), d(5), d(4), d(4), d(3), d(3), d(2, 2)]),
      line("好像许多小眼睛", [d(5), d(5), d(4), d(4), d(3), d(3), d(2, 2)]),
      line("一闪一闪亮晶晶", [d(1), d(1), d(5), d(5), d(6), d(6), d(5, 2)]),
      line("满天都是小星星", [d(4), d(4), d(3), d(3), d(2), d(2), d(1, 2)]),
    ],
  },
  {
    id: "friend",
    title: "找朋友",
    emoji: "🤝",
    credit: "传统儿歌 · 音乐盒",
    color: "#ffd0e0",
    ink: "#8c3058",
    bpm: 104,
    phrases: [
      line("找呀找呀找朋友", [d(5), d(6), d(5), d(6), d(5), d(6), d(5)]),
      line("找到一个好朋友", [d(5), d(1, 1, 1), d(7), d(6), d(5), d(5), d(3)]),
      line("敬个礼", [d(5), d(5), d(3)]),
      line("握握手", [d(5), d(5), d(3)]),
      line("你是我的好朋友", [d(2), d(4), d(3), d(2), d(1), d(3), d(1, 2)]),
    ],
  },
  {
    id: "rabbit",
    title: "小兔子乖乖",
    emoji: "🐰",
    credit: "传统儿歌 · 音乐盒",
    color: "#ffe0c2",
    ink: "#8a4518",
    bpm: 96,
    phrases: [
      line("小兔子乖乖，把门儿开开", [
        d(3), d(5), d(5), d(3), d(5), d(5), d(3), d(5), d(6), d(5), d(3, 2),
      ]),
      line("快点儿开开，我要进来", [
        d(2), d(4), d(4), d(2), d(4), d(4), d(2), d(4), d(5), d(4), d(2, 2),
      ]),
      line("不开不开我不开", [d(3), d(5), d(5), d(3), d(5), d(5), d(3), d(5)]),
      line("妈妈没回来", [d(6), d(5), d(3), d(1, 2)]),
      line("谁来也不开", [d(2), d(3), d(4), d(3), d(2), d(1), d(6, 1, -1), d(1, 2)]),
    ],
  },
  {
    id: "hanky",
    title: "丢手绢",
    emoji: "🎀",
    credit: "传统儿歌 · 音乐盒",
    color: "#ffd6ea",
    ink: "#8a2f62",
    bpm: 112,
    phrases: [
      line("丢手绢", [d(5), d(3), d(2), d(3), d(5)]),
      line("丢手绢", [d(5), d(3), d(2), d(3), d(5)]),
      line("轻轻地放后面", [d(3), d(5), d(3), d(2), d(1), d(2)]),
      line("大家不要告诉他", [d(3), d(5), d(3), d(2), d(1), d(2), d(3)]),
      line("快点快点捉住他", [d(6), d(5), d(6), d(5), d(2), d(3), d(5)]),
      line("快点快点捉住他", [d(2), d(4), d(3), d(2), d(1), d(3), d(1, 2)]),
    ],
  },
  {
    id: "radish",
    title: "一起拔萝卜",
    emoji: "🥕",
    credit: "民间故事 · 芽芽旋律",
    color: "#ffd8bf",
    ink: "#8a3d12",
    bpm: 100,
    phrases: [
      line("拔萝卜，拔萝卜", [d(5), d(5), d(6), d(5), d(3), d(1), d(2), d(1)]),
      line("嘿哟嘿哟拔不动", [d(5), d(5), d(5), d(5), d(1), d(2), d(1, 2)]),
      line("老公公，快快来", [d(5), d(5), d(6), d(5), d(3), d(1), d(2), d(1)]),
      line("一起来拔萝卜", [d(5), d(5), d(3), d(2), d(1), d(2), d(1, 2)]),
      line("老婆婆，快快来", [d(5), d(5), d(6), d(5), d(3), d(1), d(2), d(1)]),
      line("一起来拔萝卜", [d(5), d(5), d(3), d(2), d(1), d(2), d(1, 2)]),
      line("小姑娘，快快来", [d(5), d(5), d(6), d(5), d(3), d(1), d(2), d(1)]),
      line("小老鼠来帮忙", [d(5), d(5), d(6), d(5), d(3), d(2), d(1)]),
      line("嘿哟嘿哟拔起来", [d(5), d(5), d(5), d(3), d(2), d(2), d(1, 2)]),
    ],
  },
  {
    id: "boat",
    title: "划小船",
    emoji: "🚣",
    credit: "传统儿歌 · 音乐盒",
    color: "#c9f1ef",
    ink: "#0f6b6a",
    bpm: 108,
    phrases: [
      line("划呀划小船", [d(1, 0.5), d(1, 0.5), d(1, 0.5), d(2, 0.5), d(3, 1)]),
      line("慢慢往前划", [d(3, 0.5), d(2, 0.5), d(3, 0.5), d(4, 0.5), d(5, 1)]),
      line("轻轻地轻轻地轻轻地轻轻地", [
        d(1, 0.5, 1), d(1, 0.5, 1), d(1, 0.5, 1),
        d(5, 0.5), d(5, 0.5), d(5, 0.5),
        d(3, 0.5), d(3, 0.5), d(3, 0.5),
        d(1, 0.5), d(1, 0.5), d(1, 0.5),
      ]),
      line("生活多美好", [d(5, 0.5), d(4, 0.5), d(3, 0.5), d(2, 0.5), d(1, 2)]),
    ],
  },
  {
    id: "lamb",
    title: "小羊羔",
    emoji: "🐑",
    credit: "传统儿歌 · 音乐盒",
    color: "#e7f6d8",
    ink: "#3d6b16",
    bpm: 100,
    phrases: [
      line("玛丽有只小羊羔", [d(3), d(2), d(1), d(2), d(3), d(3), d(3, 2)]),
      line("小羊羔", [d(2), d(2), d(2, 2)]),
      line("小羊羔", [d(3), d(5), d(5, 2)]),
      line("玛丽有只小羊羔呀", [d(3), d(2), d(1), d(2), d(3), d(3), d(3), d(3)]),
      line("羊毛白如雪", [d(2), d(2), d(3), d(2), d(1, 2)]),
    ],
  },
  {
    id: "bridge",
    title: "伦敦桥",
    emoji: "🌉",
    credit: "传统儿歌 · 音乐盒",
    color: "#d9e4ff",
    ink: "#2c3f86",
    bpm: 108,
    phrases: [
      line("伦敦桥要倒下来", [d(5), d(6), d(5), d(4), d(3), d(4), d(5)]),
      line("倒下来，倒下来", [d(2), d(3), d(4), d(3), d(4), d(5)]),
      line("伦敦桥要倒下来", [d(5), d(6), d(5), d(4), d(3), d(4), d(5)]),
      line("我的好伙伴", [d(2), d(5), d(3), d(1, 2)]),
    ],
  },
  {
    id: "sprout",
    title: "小芽芽",
    emoji: "🌱",
    credit: "芽芽原创 · 音乐盒",
    color: "#d8f5c8",
    ink: "#1f7a3a",
    bpm: 104,
    phrases: [
      line("小芽芽，笑一笑", [d(1), d(3), d(5), d(5), d(6), d(5), d(3)]),
      line("太阳公公出来了", [d(4), d(6), d(5), d(4), d(3), d(2), d(1, 2)]),
      line("小芽芽，跳一跳", [d(1), d(3), d(5), d(5), d(6), d(5), d(3)]),
      line("我们一起玩得好", [d(4), d(3), d(2), d(7, 1, -1), d(1, 2)]),
    ],
  },
  {
    id: "lullaby",
    title: "摇篮曲",
    emoji: "🌙",
    credit: "传统曲子 · 音乐盒",
    color: "#e4dcfb",
    ink: "#4c3b86",
    bpm: 72,
    phrases: [
      line("小宝贝", [d(1, 2), d(3)]),
      line("睡一睡", [d(1, 2), d(3)]),
      line("月亮看着你", [d(1), d(3), d(5), d(6), d(5), d(3)]),
      line("小星星", [d(2, 2), d(4)]),
      line("眨眼睛", [d(2, 2), d(4)]),
      line("梦里开小花", [d(2), d(4), d(6), d(7), d(6), d(4)]),
      line("闭上眼", [d(1, 2), d(3)]),
      line("好好睡", [d(1, 2), d(3)]),
      line("芽芽陪着你", [d(1), d(3), d(6), d(5), d(4), d(3)]),
      line("明天再玩耍", [d(1), d(2), d(4), d(3), d(2), d(1, 2)]),
    ],
  },
];

export function songById(id: string): Song | undefined {
  return songs.find((song) => song.id === id);
}

export function songSeconds(song: Song): number {
  const beats = song.phrases.reduce(
    (sum, phrase) => sum + phrase.notes.reduce((inner, note) => inner + note.beats, 0),
    0,
  );
  return Math.max(1, Math.round((beats * 60) / song.bpm));
}

export function nextSongId(id: string, step: number): string {
  const index = songs.findIndex((song) => song.id === id);
  const next = (index + step + songs.length) % songs.length;
  return songs[next].id;
}
