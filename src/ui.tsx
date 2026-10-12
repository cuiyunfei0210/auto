export function Mascot({
  mood = "happy",
}: {
  mood?: "happy" | "sleep" | "wow";
}) {
  return (
    <svg className={`mascot mood-${mood}`} viewBox="0 0 160 180" aria-hidden>
      <ellipse cx="80" cy="168" rx="36" ry="8" fill="rgba(60,47,47,0.12)" />
      <g className="arm">
        <path
          d="M118 112c16 2 24 12 22 20"
          stroke="#3c2f2f"
          strokeWidth="8"
          strokeLinecap="round"
          fill="none"
        />
        <circle cx="140" cy="134" r="9" fill="#ffd7b8" stroke="#3c2f2f" strokeWidth="4" />
      </g>
      <ellipse cx="80" cy="124" rx="40" ry="34" fill="#fff7ea" stroke="#3c2f2f" strokeWidth="4" />
      <path
        d="M80 70c2-30 26-40 26-40s-6 22-24 28"
        fill="#2f9a55"
        stroke="#3c2f2f"
        strokeWidth="4"
        strokeLinejoin="round"
      />
      <path
        d="M80 70c-2-26-22-34-22-34s2 18 22 24"
        fill="#7dce73"
        stroke="#3c2f2f"
        strokeWidth="4"
        strokeLinejoin="round"
      />
      <circle cx="80" cy="86" r="34" fill="#fff7ea" stroke="#3c2f2f" strokeWidth="4" />
      <circle cx="64" cy="96" r="7" fill="#ffb7c8" />
      <circle cx="98" cy="96" r="7" fill="#ffb7c8" />
      {mood === "sleep" ? (
        <>
          <path d="M62 84c4 4 10 4 14 0" stroke="#3c2f2f" strokeWidth="4" fill="none" strokeLinecap="round" />
          <path d="M86 84c4 4 10 4 14 0" stroke="#3c2f2f" strokeWidth="4" fill="none" strokeLinecap="round" />
        </>
      ) : (
        <>
          <ellipse className="eye" cx="66" cy="84" rx="5" ry="6.5" fill="#3c2f2f" />
          <ellipse className="eye" cx="96" cy="84" rx="5" ry="6.5" fill="#3c2f2f" />
          <circle cx="68" cy="82" r="1.7" fill="#fff" />
          <circle cx="98" cy="82" r="1.7" fill="#fff" />
        </>
      )}
      {mood === "wow" ? (
        <ellipse cx="80" cy="104" rx="7" ry="8" fill="#3c2f2f" />
      ) : mood === "sleep" ? (
        <path d="M70 104h20" stroke="#3c2f2f" strokeWidth="4" strokeLinecap="round" />
      ) : (
        <path d="M68 102c6 10 18 10 24 0" stroke="#3c2f2f" strokeWidth="4" fill="none" strokeLinecap="round" />
      )}
      <ellipse cx="62" cy="152" rx="14" ry="8" fill="#ffd7b8" stroke="#3c2f2f" strokeWidth="4" />
      <ellipse cx="100" cy="152" rx="14" ry="8" fill="#ffd7b8" stroke="#3c2f2f" strokeWidth="4" />
    </svg>
  );
}

export function TopBar({ title, onBack }: { title: string; onBack: () => void }) {
  return (
    <header className="topbar">
      <button type="button" className="toy back" onClick={onBack}>
        返回
      </button>
      <h1>{title}</h1>
    </header>
  );
}

export function formatClock(ms: number): string {
  const total = Math.max(0, Math.ceil(ms / 1000));
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  if (minutes <= 0) return `${seconds} 秒`;
  return seconds === 0 ? `${minutes} 分钟` : `${minutes} 分 ${seconds} 秒`;
}
