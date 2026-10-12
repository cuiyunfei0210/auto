import { useEffect, useRef, useState, type PointerEvent } from "react";
import { getPlayer } from "./audio";

export type ShowInfo = {
  id: string;
  title: string;
  emoji: string;
  blurb: string;
  color: string;
};

export const shows: ShowInfo[] = [
  { id: "bunny", title: "小兔子找萝卜", emoji: "🐰", blurb: "跳呀跳，找到一根大萝卜", color: "#ffe7c4" },
  { id: "ocean", title: "海底泡泡", emoji: "🫧", blurb: "点一点，吹出好多泡泡", color: "#d7f4ff" },
  { id: "train", title: "小火车出发", emoji: "🚂", blurb: "小动物坐火车去旅行", color: "#ffe1c7" },
  { id: "rainbow", title: "雨过天晴", emoji: "🌈", blurb: "下雨了，然后出现彩虹", color: "#e7f6ff" },
];

export function ShowStage({ id }: { id: string }) {
  if (id === "bunny") return <BunnyShow />;
  if (id === "ocean") return <OceanShow />;
  if (id === "train") return <TrainShow />;
  return <RainbowShow />;
}

function BunnyShow() {
  const [round, setRound] = useState(0);
  const [found, setFound] = useState(false);

  useEffect(() => {
    setFound(false);
    const timer = window.setTimeout(() => {
      setFound(true);
      void getPlayer().chime();
    }, 6200);
    return () => window.clearTimeout(timer);
  }, [round]);

  return (
    <div className="stage meadow" key={round}>
      <div className="sun" />
      <div className="hill" />
      <div className={`carrot ${found ? "found" : ""}`}>🥕</div>
      <div className={`bunny-run ${found ? "found" : ""}`}>🐰</div>
      {found && <div className="found-banner">找到啦！</div>}
      <button type="button" className="toy stage-replay" onClick={() => setRound((n) => n + 1)}>
        再看一次
      </button>
    </div>
  );
}

type Bubble = { id: number; x: number; y: number; size: number };

function OceanShow() {
  const [bubbles, setBubbles] = useState<Bubble[]>([]);
  const nextId = useRef(1);

  function spawn(x: number, y: number) {
    const bubble = { id: nextId.current, x, y, size: 28 + Math.round(Math.random() * 36) };
    nextId.current += 1;
    setBubbles((list) => [...list.slice(-24), bubble]);
    void getPlayer().pop();
  }

  function onPointerDown(event: PointerEvent<HTMLDivElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * 100;
    const y = ((event.clientY - rect.top) / rect.height) * 100;
    spawn(x, y);
  }

  return (
    <div className="stage ocean" onPointerDown={onPointerDown}>
      <div className="fish f1">🐟</div>
      <div className="fish f2">🐠</div>
      <div className="fish f3">🐡</div>
      <div className="seaweed s1" />
      <div className="seaweed s2" />
      <div className="seaweed s3" />
      {bubbles.map((bubble) => (
        <span
          key={bubble.id}
          className="bubble"
          style={{ left: `${bubble.x}%`, top: `${bubble.y}%`, width: bubble.size, height: bubble.size }}
          onAnimationEnd={() => setBubbles((list) => list.filter((item) => item.id !== bubble.id))}
        />
      ))}
      <p className="stage-hint">点一点海水</p>
    </div>
  );
}

function TrainShow() {
  return (
    <div className="stage railway">
      <div className="cloud-move c1" />
      <div className="cloud-move c2" />
      <div className="rail-hill" />
      <div className="train">
        <span>🐰</span>
        <span>🐱</span>
        <span>🐥</span>
        <span className="engine">🚂</span>
      </div>
      <button
        type="button"
        className="toy whistle"
        onClick={(event) => {
          event.stopPropagation();
          void getPlayer().whistle();
        }}
      >
        呜呜
      </button>
    </div>
  );
}

type Weather = "sun" | "cloud" | "rain" | "bow";

function RainbowShow() {
  const [weather, setWeather] = useState<Weather>("sun");
  const [round, setRound] = useState(0);
  const [flowers, setFlowers] = useState<number[]>([]);

  useEffect(() => {
    setWeather("sun");
    setFlowers([]);
    const steps: { at: number; weather: Weather }[] = [
      { at: 1600, weather: "cloud" },
      { at: 3200, weather: "rain" },
      { at: 7000, weather: "bow" },
    ];
    const timers = steps.map((step) =>
      window.setTimeout(() => {
        setWeather(step.weather);
        void getPlayer().setRain(step.weather === "rain");
        if (step.weather === "bow") void getPlayer().chime();
      }, step.at),
    );
    return () => {
      timers.forEach((timer) => window.clearTimeout(timer));
      void getPlayer().setRain(false);
    };
  }, [round]);

  return (
    <div className={`stage weather ${weather}`} key={round}>
      <div className="sun" />
      <div className="rain-cloud" />
      {weather === "rain" && (
        <div className="rain">
          {Array.from({ length: 18 }, (_, index) => (
            <i key={index} style={{ left: `${(index * 17) % 100}%`, animationDelay: `${(index % 6) * 0.12}s` }} />
          ))}
        </div>
      )}
      {weather === "bow" && <div className="rainbow" />}
      <div className="hill" />
      <div className="flower-row">
        {["🌷", "🌻", "🌼", "🌺"].map((flower, index) => (
          <button
            key={flower}
            type="button"
            className={`flower ${flowers.includes(index) ? "up" : ""} ${weather === "bow" ? "grow" : ""}`}
            onClick={() => {
              setFlowers((list) => (list.includes(index) ? list : [...list, index]));
              void getPlayer().pop();
            }}
          >
            {flower}
          </button>
        ))}
      </div>
      <button type="button" className="toy stage-replay" onClick={() => setRound((n) => n + 1)}>
        再看一次
      </button>
    </div>
  );
}
