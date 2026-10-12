import { useState } from "react";
import { hush, speak } from "./audio";

export type StoryPage = {
  text: string;
  scene: "balloon" | "wind" | "bird" | "thanks" | "moon" | "boat" | "wave" | "home";
};

export type Story = {
  id: string;
  title: string;
  emoji: string;
  color: string;
  pages: StoryPage[];
};

export const stories: Story[] = [
  {
    id: "balloon",
    title: "红气球",
    emoji: "🎈",
    color: "#ffe1ea",
    pages: [
      { text: "芽芽拿到一只红气球。", scene: "balloon" },
      { text: "风一吹，气球飞高了。", scene: "wind" },
      { text: "小鸟衔住绳子，把气球送回来。", scene: "bird" },
      { text: "芽芽说：谢谢你，我们一起玩。", scene: "thanks" },
    ],
  },
  {
    id: "moonboat",
    title: "月亮船",
    emoji: "🌙",
    color: "#e6e0ff",
    pages: [
      { text: "晚上，芽芽看见弯弯的月亮。", scene: "moon" },
      { text: "月亮变成一条小船。", scene: "boat" },
      { text: "芽芽坐在船上，向星星招手。", scene: "wave" },
      { text: "船靠岸了，芽芽回家睡觉。", scene: "home" },
    ],
  },
];

export function storyById(id: string): Story | undefined {
  return stories.find((story) => story.id === id);
}

export function StoryReader({ story, onBack }: { story: Story; onBack: () => void }) {
  const [page, setPage] = useState(0);
  const current = story.pages[page];

  function go(next: number) {
    hush();
    setPage(next);
  }

  return (
    <section className="reader">
      <div className="story-stage" style={{ background: story.color }}>
        <StoryArt scene={current.scene} />
      </div>
      <p className="story-line">{current.text}</p>
      <div className="dots" aria-hidden>
        {story.pages.map((item, index) => (
          <i key={item.text} className={index === page ? "on" : ""} />
        ))}
      </div>
      <div className="reader-actions">
        <button type="button" className="toy" disabled={page === 0} onClick={() => go(page - 1)}>
          上一页
        </button>
        <button type="button" className="toy accent" onClick={() => speak(current.text)}>
          读一读
        </button>
        {page < story.pages.length - 1 ? (
          <button type="button" className="toy" onClick={() => go(page + 1)}>
            下一页
          </button>
        ) : (
          <button type="button" className="toy" onClick={onBack}>
            读完啦
          </button>
        )}
      </div>
    </section>
  );
}

function StoryArt({ scene }: { scene: StoryPage["scene"] }) {
  const night = scene === "moon" || scene === "boat" || scene === "wave" || scene === "home";
  return (
    <svg viewBox="0 0 360 230" className="story-art" aria-hidden>
      <rect width="360" height="230" fill={night ? "#2a3566" : "#9adfff"} />
      <ellipse cx="180" cy="250" rx="230" ry="90" fill={night ? "#3d4c86" : "#b6e58a"} />
      {night && (
        <>
          <circle cx="300" cy="48" r="26" fill="#fff3c4" />
          <circle cx="40" cy="40" r="2" fill="#fff" />
          <circle cx="80" cy="70" r="2" fill="#fff" />
          <circle cx="140" cy="36" r="1.5" fill="#fff" />
        </>
      )}
      {!night && <circle cx="300" cy="46" r="24" fill="#ffe14a" />}
      {scene === "balloon" && (
        <>
          <Buddy x={150} y={150} />
          <Balloon x={214} y={78} />
        </>
      )}
      {scene === "wind" && (
        <>
          <Buddy x={90} y={156} />
          <path d="M40 120c30-10 40 10 70 0" stroke="#fff" strokeWidth="6" fill="none" strokeLinecap="round" />
          <Balloon x={250} y={48} />
        </>
      )}
      {scene === "bird" && (
        <>
          <Buddy x={120} y={156} />
          <Bird x={230} y={70} />
          <Balloon x={278} y={78} />
        </>
      )}
      {scene === "thanks" && (
        <>
          <Buddy x={140} y={150} />
          <Bird x={230} y={120} />
          <Balloon x={188} y={70} />
        </>
      )}
      {scene === "moon" && <Buddy x={160} y={156} />}
      {scene === "boat" && (
        <>
          <path d="M120 150h140l-20 24H140z" fill="#ffe08a" stroke="#3c2f2f" strokeWidth="3" />
          <circle cx="250" cy="52" r="18" fill="none" stroke="#fff3c4" strokeWidth="8" />
        </>
      )}
      {scene === "wave" && (
        <>
          <path d="M110 156h150l-18 22H130z" fill="#ffe08a" stroke="#3c2f2f" strokeWidth="3" />
          <Buddy x={176} y={132} />
          <circle cx="300" cy="40" r="3" fill="#fff" />
          <circle cx="70" cy="56" r="2.4" fill="#fff" />
        </>
      )}
      {scene === "home" && (
        <>
          <House />
          <Buddy x={250} y={156} />
        </>
      )}
    </svg>
  );
}

function Buddy({ x, y }: { x: number; y: number }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <ellipse cx="0" cy="28" rx="22" ry="8" fill="rgba(0,0,0,0.12)" />
      <circle cx="0" cy="0" r="22" fill="#fff7ea" stroke="#3c2f2f" strokeWidth="3" />
      <path d="M0 -18c0-16 12-20 12-20s-2 10-12 14" fill="#3dae6a" stroke="#3c2f2f" strokeWidth="3" />
      <circle cx="-8" cy="-2" r="2.4" fill="#3c2f2f" />
      <circle cx="8" cy="-2" r="2.4" fill="#3c2f2f" />
      <path d="M-6 8c4 5 10 5 14 0" stroke="#3c2f2f" strokeWidth="2.4" fill="none" strokeLinecap="round" />
    </g>
  );
}

function Balloon({ x, y }: { x: number; y: number }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <ellipse cx="0" cy="0" rx="22" ry="28" fill="#ff5d73" stroke="#3c2f2f" strokeWidth="3" />
      <path d="M0 28c8 16-6 20 0 32" stroke="#3c2f2f" strokeWidth="2" fill="none" />
      <ellipse cx="-6" cy="-8" rx="5" ry="8" fill="#fff" opacity="0.7" />
    </g>
  );
}

function Bird({ x, y }: { x: number; y: number }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <ellipse cx="0" cy="0" rx="22" ry="12" fill="#7ec8ff" stroke="#3c2f2f" strokeWidth="3" />
      <circle cx="16" cy="-4" r="8" fill="#7ec8ff" stroke="#3c2f2f" strokeWidth="3" />
      <circle cx="18" cy="-6" r="1.6" fill="#3c2f2f" />
      <path d="M24 -4h10" stroke="#ffb000" strokeWidth="3" strokeLinecap="round" />
      <path d="M-8 4c10 16 20 8 28 0" stroke="#3c2f2f" strokeWidth="3" fill="none" />
    </g>
  );
}

function House() {
  return (
    <g>
      <rect x="70" y="120" width="90" height="64" fill="#fff7ea" stroke="#3c2f2f" strokeWidth="3" />
      <polygon points="64,120 115,78 166,120" fill="#ff8b7b" stroke="#3c2f2f" strokeWidth="3" />
      <rect x="104" y="148" width="22" height="36" fill="#c9843a" stroke="#3c2f2f" strokeWidth="3" />
      <rect x="80" y="136" width="18" height="16" fill="#9adfff" stroke="#3c2f2f" strokeWidth="3" />
    </g>
  );
}
