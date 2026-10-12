import { useState } from "react";
import { getPlayer, type AnimalId } from "./audio";

const animals: { id: AnimalId; name: string; word: string; emoji: string }[] = [
  { id: "cat", name: "小猫", word: "喵", emoji: "🐱" },
  { id: "dog", name: "小狗", word: "汪", emoji: "🐶" },
  { id: "duck", name: "小鸭", word: "嘎", emoji: "🦆" },
  { id: "cow", name: "小牛", word: "哞", emoji: "🐮" },
  { id: "frog", name: "青蛙", word: "呱", emoji: "🐸" },
  { id: "bird", name: "小鸟", word: "叽", emoji: "🐦" },
  { id: "sheep", name: "小羊", word: "咩", emoji: "🐑" },
  { id: "tiger", name: "小虎", word: "嗷", emoji: "🐯" },
];

const keys = [
  { name: "哆", midi: 72, color: "#ff6b57" },
  { name: "来", midi: 74, color: "#ffb000" },
  { name: "咪", midi: 76, color: "#ffe14a" },
  { name: "嗦", midi: 79, color: "#3dae6a" },
  { name: "啦", midi: 81, color: "#4cb8e8" },
];

export function Playroom() {
  const [active, setActive] = useState<AnimalId | null>(null);
  const [word, setWord] = useState("点一点");

  return (
    <div className="play-layout">
      <section>
        <h2 className="section-title">小动物</h2>
        <p className="animal-word" aria-live="polite">
          {word}
        </p>
        <div className="animal-grid">
          {animals.map((animal) => (
            <button
              key={animal.id}
              type="button"
              className={`toy animal ${active === animal.id ? "pop" : ""}`}
              onClick={() => {
                setActive(animal.id);
                setWord(`${animal.name}：${animal.word}`);
                void getPlayer().animal(animal.id);
                window.setTimeout(() => setActive((current) => (current === animal.id ? null : current)), 280);
              }}
            >
              <span className="animal-emoji">{animal.emoji}</span>
              <span>{animal.name}</span>
            </button>
          ))}
        </div>
      </section>
      <section>
        <h2 className="section-title">小木琴</h2>
        <div className="xylo">
          {keys.map((key) => (
            <button
              key={key.name}
              type="button"
              className="xylo-key"
              style={{ background: key.color }}
              onPointerDown={() => {
                void getPlayer().bell(key.midi, 1.2);
              }}
            >
              {key.name}
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
