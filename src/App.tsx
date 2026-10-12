import { useEffect, useMemo, useState } from "react";
import { getPlayer, hush, type PlayerSnap } from "./audio";
import { Playroom } from "./playroom";
import { SongPicture } from "./pictures";
import { ShowStage, shows } from "./shows";
import { nextSongId, songById, songSeconds, songs } from "./songs";
import { StoryReader, stories, storyById } from "./stories";
import { Mascot, TopBar, formatClock } from "./ui";

type Screen =
  | { name: "home" }
  | { name: "songs" }
  | { name: "player"; songId: string }
  | { name: "shows" }
  | { name: "show"; showId: string }
  | { name: "stories" }
  | { name: "story"; storyId: string }
  | { name: "play" };

const emptySnap: PlayerSnap = { songId: null, phrase: 0, playing: false, beat: 0 };

export function App() {
  const [stack, setStack] = useState<Screen[]>([{ name: "home" }]);
  const [snap, setSnap] = useState<PlayerSnap>(emptySnap);
  const [parentsOpen, setParentsOpen] = useState(false);
  const [hold, setHold] = useState(0);
  const [restAt, setRestAt] = useState<number | null>(null);
  const [resting, setResting] = useState(false);
  const [now, setNow] = useState(() => Date.now());
  const [volume, setVolume] = useState(() => getPlayer().getVolume());
  const screen = stack[stack.length - 1];

  useEffect(() => getPlayer().subscribe(setSnap), []);

  useEffect(() => {
    if (!restAt) return;
    const timer = window.setInterval(() => {
      const time = Date.now();
      setNow(time);
      if (time >= restAt) {
        getPlayer().stop();
        hush();
        setResting(true);
        setRestAt(null);
      }
    }, 400);
    return () => window.clearInterval(timer);
  }, [restAt]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape" && stack.length > 1 && !resting && !parentsOpen) {
        setStack((current) => current.slice(0, -1));
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [parentsOpen, resting, stack.length]);

  function push(next: Screen) {
    if (next.name === "show" || next.name === "play" || next.name === "story") {
      getPlayer().stop();
      hush();
    }
    if (!getPlayer().getSnap().playing) void getPlayer().pop();
    setStack((current) => [...current, next]);
  }

  function back() {
    hush();
    void getPlayer().setRain(false);
    if (!getPlayer().getSnap().playing) void getPlayer().pop();
    setStack((current) => (current.length > 1 ? current.slice(0, -1) : current));
  }

  function openSong(songId: string, keep = false) {
    const song = songById(songId);
    if (!song) return;
    void getPlayer().setRain(false);
    const currentSnap = getPlayer().getSnap();
    if (!(keep && currentSnap.songId === songId)) void getPlayer().play(song);
    setStack((current) => {
      const top = current[current.length - 1];
      if (top.name === "player") return [...current.slice(0, -1), { name: "player", songId }];
      return [...current, { name: "player", songId }];
    });
  }

  const greeting = useMemo(() => {
    const hour = new Date().getHours();
    if (hour < 11) return "早上好";
    if (hour < 14) return "中午好";
    if (hour < 18) return "下午好";
    return "晚上好";
  }, []);

  const playingSong = snap.songId ? songById(snap.songId) : undefined;
  const showMini = Boolean(playingSong) && screen.name !== "player" && !resting;

  return (
    <div className="garden">
      <div className="sky-decor" aria-hidden>
        <span className="cloud c1" />
        <span className="cloud c2" />
      </div>
      <main className="app-frame">
        {resting ? (
          <RestScreen
            onWake={() => {
              setResting(false);
              setParentsOpen(false);
            }}
          />
        ) : (
          <>
            {screen.name === "home" && (
              <Home
                greeting={greeting}
                restLabel={restAt ? formatClock(restAt - now) : null}
                onOpen={push}
                onParents={() => setParentsOpen(true)}
              />
            )}
            {screen.name === "songs" && <SongList onBack={back} onOpen={openSong} />}
            {screen.name === "player" && (
              <Player
                songId={screen.songId}
                snap={snap}
                onBack={back}
                onOpen={openSong}
              />
            )}
            {screen.name === "shows" && (
              <ShowList
                onBack={back}
                onOpen={(showId) => push({ name: "show", showId })}
              />
            )}
            {screen.name === "show" && (
              <section>
                <TopBar title={shows.find((item) => item.id === screen.showId)?.title ?? "动画"} onBack={back} />
                <ShowStage id={screen.showId} />
              </section>
            )}
            {screen.name === "stories" && (
              <StoryList onBack={back} onOpen={(storyId) => push({ name: "story", storyId })} />
            )}
            {screen.name === "story" && storyById(screen.storyId) && (
              <section>
                <TopBar title={storyById(screen.storyId)!.title} onBack={back} />
                <StoryReader story={storyById(screen.storyId)!} onBack={back} />
              </section>
            )}
            {screen.name === "play" && (
              <section>
                <TopBar title="点一点" onBack={back} />
                <Playroom />
              </section>
            )}
          </>
        )}
      </main>
      {showMini && playingSong && (
        <div className="mini">
          <button type="button" className="mini-main" onClick={() => openSong(playingSong.id, true)}>
            <span>{playingSong.emoji}</span>
            <span>{playingSong.title}</span>
          </button>
          <button type="button" className="toy mini-toggle" onClick={() => void getPlayer().toggle()}>
            {snap.playing ? "暂停" : "继续"}
          </button>
        </div>
      )}
      {parentsOpen && !resting && (
        <ParentSheet
          hold={hold}
          setHold={setHold}
          volume={volume}
          restAt={restAt}
          now={now}
          onClose={() => {
            setParentsOpen(false);
            setHold(0);
          }}
          onVolume={(value) => {
            setVolume(value);
            void getPlayer().setVolume(value);
          }}
          onRest={(minutes) => {
            setRestAt(minutes ? Date.now() + minutes * 60_000 : null);
            setParentsOpen(false);
            setHold(0);
          }}
        />
      )}
    </div>
  );
}

function Home({
  greeting,
  restLabel,
  onOpen,
  onParents,
}: {
  greeting: string;
  restLabel: string | null;
  onOpen: (screen: Screen) => void;
  onParents: () => void;
}) {
  return (
    <div className="home-layout">
      <section className="hero">
        <Mascot />
        <div>
          <p className="eyebrow">{greeting}</p>
          <h1 className="logo">芽芽乐园</h1>
          <p className="lede">听儿歌，看动画，还可以读故事。</p>
          {restLabel && <p className="rest-chip">再玩 {restLabel}</p>}
        </div>
      </section>
      <div className="tile-grid">
        <button type="button" className="tile sun" onClick={() => onOpen({ name: "songs" })}>
          <span className="tile-emoji">🎵</span>
          <span className="tile-title">儿歌</span>
          <span className="tile-meta">{songs.length} 首，点一下就唱</span>
        </button>
        <button type="button" className="tile sky" onClick={() => onOpen({ name: "shows" })}>
          <span className="tile-emoji">🎬</span>
          <span className="tile-title">动画</span>
          <span className="tile-meta">{shows.length} 部小动画</span>
        </button>
        <button type="button" className="tile grape" onClick={() => onOpen({ name: "stories" })}>
          <span className="tile-emoji">📖</span>
          <span className="tile-title">故事</span>
          <span className="tile-meta">{stories.length} 个图画故事</span>
        </button>
        <button type="button" className="tile leaf" onClick={() => onOpen({ name: "play" })}>
          <span className="tile-emoji">🐾</span>
          <span className="tile-title">点一点</span>
          <span className="tile-meta">小动物和小木琴</span>
        </button>
      </div>
      <button type="button" className="parent-link" onClick={onParents}>
        家长
      </button>
    </div>
  );
}

function SongList({ onBack, onOpen }: { onBack: () => void; onOpen: (id: string) => void }) {
  return (
    <section>
      <TopBar title="儿歌" onBack={onBack} />
      <div className="song-list">
        {songs.map((song) => (
          <button
            key={song.id}
            type="button"
            className="song-row"
            style={{ background: song.color, color: song.ink }}
            onClick={() => onOpen(song.id)}
          >
            <span className="song-emoji">{song.emoji}</span>
            <span>
              <strong>{song.title}</strong>
              <small>
                {song.credit} · 约 {songSeconds(song)} 秒
              </small>
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}

function Player({
  songId,
  snap,
  onBack,
  onOpen,
}: {
  songId: string;
  snap: PlayerSnap;
  onBack: () => void;
  onOpen: (id: string) => void;
}) {
  const song = songById(songId);
  useEffect(() => {
    const node = document.getElementById(`line-${snap.phrase}`);
    const parent = node?.parentElement;
    if (!node || !parent) return;
    parent.scrollTo({
      top: node.offsetTop - parent.clientHeight / 2 + node.clientHeight / 2,
      behavior: "smooth",
    });
  }, [snap.phrase, songId]);

  if (!song) {
    return (
      <section>
        <TopBar title="儿歌" onBack={onBack} />
        <p>这首歌走丢了。</p>
      </section>
    );
  }

  const active = snap.songId === song.id;
  const pulse = active && snap.playing && snap.beat % 2 === 1;

  return (
    <section className="player">
      <TopBar title="正在唱" onBack={onBack} />
      <div className={`art-card ${pulse ? "pulse" : ""}`} style={{ background: song.color }}>
        <SongPicture id={song.id} />
      </div>
      <h2 style={{ color: song.ink }}>{song.title}</h2>
      <p className="credit">{song.credit}</p>
      <div className="lyrics">
        {song.phrases.map((phrase, index) => (
          <p id={`line-${index}`} key={`${song.id}-${phrase.lyric}-${index}`} className={active && snap.phrase === index ? "on" : ""}>
            {phrase.lyric}
          </p>
        ))}
      </div>
      <div className="transport">
        <button type="button" className="toy" onClick={() => onOpen(nextSongId(song.id, -1))}>
          上一首
        </button>
        <button
          type="button"
          className="toy play"
          onClick={() => {
            if (active) void getPlayer().toggle();
            else void getPlayer().play(song);
          }}
        >
          {active && snap.playing ? "暂停" : "播放"}
        </button>
        <button type="button" className="toy" onClick={() => onOpen(nextSongId(song.id, 1))}>
          下一首
        </button>
      </div>
    </section>
  );
}

function ShowList({ onBack, onOpen }: { onBack: () => void; onOpen: (id: string) => void }) {
  return (
    <section>
      <TopBar title="动画" onBack={onBack} />
      <div className="card-list">
        {shows.map((show) => (
          <button key={show.id} type="button" className="story-card" style={{ background: show.color }} onClick={() => onOpen(show.id)}>
            <span className="song-emoji">{show.emoji}</span>
            <span>
              <strong>{show.title}</strong>
              <small>{show.blurb}</small>
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}

function StoryList({ onBack, onOpen }: { onBack: () => void; onOpen: (id: string) => void }) {
  return (
    <section>
      <TopBar title="故事" onBack={onBack} />
      <div className="card-list">
        {stories.map((story) => (
          <button key={story.id} type="button" className="story-card" style={{ background: story.color }} onClick={() => onOpen(story.id)}>
            <span className="song-emoji">{story.emoji}</span>
            <span>
              <strong>{story.title}</strong>
              <small>{story.pages.length} 页图画</small>
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}

function ParentSheet({
  hold,
  setHold,
  volume,
  restAt,
  now,
  onClose,
  onVolume,
  onRest,
}: {
  hold: number;
  setHold: (value: number | ((current: number) => number)) => void;
  volume: number;
  restAt: number | null;
  now: number;
  onClose: () => void;
  onVolume: (value: number) => void;
  onRest: (minutes: number | null) => void;
}) {
  const [unlocked, setUnlocked] = useState(false);

  useEffect(() => {
    if (hold < 100 || unlocked) return;
    setUnlocked(true);
  }, [hold, unlocked]);

  useEffect(() => {
    if (hold <= 0 || hold >= 100 || unlocked) return;
    const timer = window.setInterval(() => setHold((current) => Math.min(100, current + 2)), 40);
    return () => window.clearInterval(timer);
  }, [hold, setHold, unlocked]);

  return (
    <div className="sheet-backdrop" role="presentation">
      <section className="sheet parents" role="dialog" aria-label="家长">
        <h2>给爸爸妈妈</h2>
        {unlocked ? (
          <>
            <p>这里没有广告，儿歌、动画和故事都放在本机里。儿歌用音乐盒音色演奏传统曲子。</p>
            <label className="volume">
              音量
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={volume}
                onChange={(event) => onVolume(Number(event.target.value))}
              />
            </label>
            <p>{restAt ? `休息倒计时还剩 ${formatClock(restAt - now)}` : "可以设一个休息时间。"}</p>
            <div className="rest-choices">
              <button type="button" className="toy" onClick={() => onRest(5)}>
                5 分钟
              </button>
              <button type="button" className="toy" onClick={() => onRest(10)}>
                10 分钟
              </button>
              <button type="button" className="toy" onClick={() => onRest(15)}>
                15 分钟
              </button>
              <button type="button" className="toy" onClick={() => onRest(null)}>
                不限时
              </button>
            </div>
          </>
        ) : (
          <>
            <p>请按住小太阳，大约两秒。</p>
            <button
              type="button"
              className="hold-sun"
              onPointerDown={() => setHold(4)}
              onPointerUp={() => setHold(0)}
              onPointerLeave={() => setHold(0)}
            >
              <span className="hold-fill" style={{ height: `${hold}%` }} />
              <span className="hold-face">☀️</span>
            </button>
          </>
        )}
        <button type="button" className="toy close-sheet" onClick={onClose}>
          好的
        </button>
      </section>
    </div>
  );
}

function RestScreen({ onWake }: { onWake: () => void }) {
  const [hold, setHold] = useState(0);
  useEffect(() => {
    if (hold >= 100) onWake();
  }, [hold, onWake]);
  useEffect(() => {
    if (hold <= 0 || hold >= 100) return;
    const timer = window.setInterval(() => setHold((current) => Math.min(100, current + 2)), 40);
    return () => window.clearInterval(timer);
  }, [hold]);

  return (
    <section className="rest-screen">
      <Mascot mood="sleep" />
      <h1>芽芽睡觉了</h1>
      <p>今天玩得很开心。明天再来吧。</p>
      <button
        type="button"
        className="hold-sun"
        onPointerDown={() => setHold(4)}
        onPointerUp={() => setHold(0)}
        onPointerLeave={() => setHold(0)}
      >
        <span className="hold-fill" style={{ height: `${hold}%` }} />
        <span className="hold-face">☀️</span>
      </button>
      <small>爸爸妈妈按住小太阳，就可以继续。</small>
    </section>
  );
}
