export function SongPicture({ id }: { id: string }) {
  return (
    <svg className="picture" viewBox="0 0 320 220" aria-hidden>
      <Sky id={id} />
      {id === "tigers" && <Tigers />}
      {id === "star" && <Stars />}
      {id === "friend" && <Friends />}
      {id === "rabbit" && <Rabbit />}
      {id === "hanky" && <Hanky />}
      {id === "radish" && <Radish />}
      {id === "boat" && <Boat />}
      {id === "lamb" && <Lamb />}
      {id === "bridge" && <Bridge />}
      {id === "sprout" && <SproutArt />}
      {id === "lullaby" && <MoonArt />}
    </svg>
  );
}

function Sky({ id }: { id: string }) {
  const night = id === "lullaby" || id === "star";
  return (
    <>
      <rect width="320" height="220" fill={night ? "#24315f" : "#8fd4ff"} />
      <ellipse cx="160" cy="250" rx="220" ry="90" fill={night ? "#31407a" : "#b7e38a"} />
      <ellipse cx="70" cy="188" rx="70" ry="28" fill={night ? "#3c4d8c" : "#d7f5a8"} />
      <ellipse cx="240" cy="196" rx="80" ry="30" fill={night ? "#3c4d8c" : "#d7f5a8"} />
      {night ? (
        <>
          <circle cx="250" cy="48" r="22" fill="#fff4c4" />
          <circle cx="48" cy="40" r="2" fill="#fff" />
          <circle cx="90" cy="28" r="2" fill="#fff" />
          <circle cx="140" cy="46" r="1.6" fill="#fff" />
          <circle cx="200" cy="26" r="1.8" fill="#fff" />
        </>
      ) : (
        <circle cx="262" cy="42" r="22" fill="#ffe14a" />
      )}
    </>
  );
}

function Tigers() {
  return (
    <g>
      <Tiger x={108} />
      <Tiger x={196} />
    </g>
  );
}

function Tiger({ x }: { x: number }) {
  return (
    <g transform={`translate(${x} 118)`}>
      <ellipse cx="0" cy="28" rx="28" ry="18" fill="#ffb23e" stroke="#3c2f2f" strokeWidth="3" />
      <circle cx="0" cy="0" r="22" fill="#ffb23e" stroke="#3c2f2f" strokeWidth="3" />
      <path d="M-14 -8h6M-3 -12h6M8 -8h6" stroke="#3c2f2f" strokeWidth="3" strokeLinecap="round" />
      <circle cx="-8" cy="-2" r="3" fill="#3c2f2f" />
      <circle cx="8" cy="-2" r="3" fill="#3c2f2f" />
      <ellipse cx="0" cy="8" rx="6" ry="4" fill="#fff" stroke="#3c2f2f" strokeWidth="2" />
      <circle cx="-12" cy="-16" r="6" fill="#ffb23e" stroke="#3c2f2f" strokeWidth="3" />
      <circle cx="12" cy="-16" r="6" fill="#ffb23e" stroke="#3c2f2f" strokeWidth="3" />
      <path d="M18 24c16 8 22 2 24 -8" stroke="#ffb23e" strokeWidth="6" strokeLinecap="round" />
    </g>
  );
}

function Stars() {
  return (
    <g fill="#ffe14a" stroke="#3c2f2f" strokeWidth="3" strokeLinejoin="round">
      <Star cx={70} cy={70} s={1} />
      <Star cx={160} cy={54} s={1.5} />
      <Star cx={240} cy={86} s={1.1} />
    </g>
  );
}

function Star({ cx, cy, s }: { cx: number; cy: number; s: number }) {
  return (
    <polygon
      transform={`translate(${cx} ${cy}) scale(${s})`}
      points="0,-18 5,-6 18,-6 8,2 12,16 0,8 -12,16 -8,2 -18,-6 -5,-6"
    />
  );
}

function Friends() {
  return (
    <g>
      <Kid x={110} color="#ff8b7b" />
      <Kid x={200} color="#7dce73" />
    </g>
  );
}

function Kid({ x, color }: { x: number; color: string }) {
  return (
    <g transform={`translate(${x} 126)`}>
      <circle cx="0" cy="-28" r="16" fill="#ffd7b8" stroke="#3c2f2f" strokeWidth="3" />
      <rect x="-16" y="-12" width="32" height="28" rx="10" fill={color} stroke="#3c2f2f" strokeWidth="3" />
      <circle cx="-6" cy="-30" r="2" fill="#3c2f2f" />
      <circle cx="6" cy="-30" r="2" fill="#3c2f2f" />
      <path d="M-5 -22c3 4 8 4 11 0" stroke="#3c2f2f" strokeWidth="2" fill="none" strokeLinecap="round" />
    </g>
  );
}

function Rabbit() {
  return (
    <g transform="translate(160 132)">
      <ellipse cx="-10" cy="-48" rx="7" ry="20" fill="#fff" stroke="#3c2f2f" strokeWidth="3" />
      <ellipse cx="10" cy="-48" rx="7" ry="20" fill="#fff" stroke="#3c2f2f" strokeWidth="3" />
      <ellipse cx="-10" cy="-48" rx="3" ry="12" fill="#ffb7c8" />
      <ellipse cx="10" cy="-48" rx="3" ry="12" fill="#ffb7c8" />
      <circle cx="0" cy="-16" r="22" fill="#fff" stroke="#3c2f2f" strokeWidth="3" />
      <circle cx="-8" cy="-18" r="2.4" fill="#3c2f2f" />
      <circle cx="8" cy="-18" r="2.4" fill="#3c2f2f" />
      <path d="M-4 -10h8" stroke="#3c2f2f" strokeWidth="2" strokeLinecap="round" />
      <ellipse cx="0" cy="16" rx="18" ry="14" fill="#fff" stroke="#3c2f2f" strokeWidth="3" />
    </g>
  );
}

function Hanky() {
  return (
    <g transform="translate(160 120)">
      <circle cx="-36" cy="10" r="22" fill="#ffd7b8" stroke="#3c2f2f" strokeWidth="3" />
      <circle cx="40" cy="16" r="20" fill="#ffd7b8" stroke="#3c2f2f" strokeWidth="3" />
      <path d="M-8 0c20-28 40-20 52 4" stroke="#ff6b9a" strokeWidth="8" fill="none" strokeLinecap="round" />
      <path d="M28 -8l18-16 10 12-16 10z" fill="#ff6b9a" stroke="#3c2f2f" strokeWidth="3" />
    </g>
  );
}

function Radish() {
  return (
    <g transform="translate(156 150)">
      <path d="M0 -8c20 10 28 36 18 58-16 8-40 4-46-16C-34 8-20-16 0-8z" fill="#ff7a45" stroke="#3c2f2f" strokeWidth="3" />
      <path d="M-2 -16c-16-24-6-36 2-40 10 6 16 22 2 40z" fill="#3dae6a" stroke="#3c2f2f" strokeWidth="3" />
      <path d="M6 -18c8-20 24-24 28-18-12 2-24 10-28 18z" fill="#7dce73" stroke="#3c2f2f" strokeWidth="3" />
    </g>
  );
}

function Boat() {
  return (
    <g>
      <path d="M40 150c40 8 70 8 240 0" stroke="#1f8ec8" strokeWidth="6" fill="none" strokeLinecap="round" />
      <path d="M40 142c30 10 50 10 80 0" stroke="#4cb8e8" strokeWidth="4" fill="none" />
      <path d="M90 132l70 16 70-16-20 8H110z" fill="#ffb000" stroke="#3c2f2f" strokeWidth="3" />
      <path d="M160 132V78" stroke="#3c2f2f" strokeWidth="3" />
      <path d="M160 80l48 40H160z" fill="#fff" stroke="#3c2f2f" strokeWidth="3" />
    </g>
  );
}

function Lamb() {
  return (
    <g transform="translate(160 136)">
      <circle cx="-16" cy="-6" r="12" fill="#fff" stroke="#3c2f2f" strokeWidth="3" />
      <circle cx="0" cy="-12" r="14" fill="#fff" stroke="#3c2f2f" strokeWidth="3" />
      <circle cx="16" cy="-4" r="12" fill="#fff" stroke="#3c2f2f" strokeWidth="3" />
      <circle cx="0" cy="8" r="16" fill="#fff" stroke="#3c2f2f" strokeWidth="3" />
      <ellipse cx="34" cy="6" rx="14" ry="10" fill="#ffd7b8" stroke="#3c2f2f" strokeWidth="3" />
      <circle cx="38" cy="4" r="2" fill="#3c2f2f" />
      <ellipse cx="46" cy="8" rx="4" ry="3" fill="#ffb7c8" />
    </g>
  );
}

function Bridge() {
  return (
    <g>
      <path d="M30 150h260" stroke="#8d6a43" strokeWidth="10" strokeLinecap="round" />
      <path d="M50 150c0-40 40-70 70-70s70 30 70 70" fill="none" stroke="#ffb000" strokeWidth="10" />
      <path d="M70 150V110M120 150V92M170 150V110" stroke="#8d6a43" strokeWidth="6" />
      <rect x="214" y="96" width="36" height="28" rx="6" fill="#ff8b7b" stroke="#3c2f2f" strokeWidth="3" />
      <polygon points="208,96 232,74 256,96" fill="#ff6b57" stroke="#3c2f2f" strokeWidth="3" />
    </g>
  );
}

function SproutArt() {
  return (
    <g transform="translate(160 150)">
      <ellipse cx="0" cy="10" rx="26" ry="16" fill="#c9843a" stroke="#3c2f2f" strokeWidth="3" />
      <path d="M0 4C2-28 24-40 28-48" stroke="#2f9a55" strokeWidth="6" fill="none" strokeLinecap="round" />
      <ellipse cx="30" cy="-50" rx="16" ry="10" fill="#7dce73" stroke="#3c2f2f" strokeWidth="3" transform="rotate(-30 30 -50)" />
      <ellipse cx="-8" cy="-24" rx="14" ry="8" fill="#3dae6a" stroke="#3c2f2f" strokeWidth="3" transform="rotate(30 -8 -24)" />
    </g>
  );
}

function MoonArt() {
  return (
    <g>
      <circle cx="78" cy="78" r="28" fill="#fff4c4" />
      <circle cx="90" cy="70" r="22" fill="#24315f" />
      <rect x="126" y="118" width="70" height="28" rx="14" fill="#8b6b4a" stroke="#3c2f2f" strokeWidth="3" />
      <circle cx="150" cy="112" r="14" fill="#fff7ea" stroke="#3c2f2f" strokeWidth="3" />
      <path d="M144 110h4M156 110h4" stroke="#3c2f2f" strokeWidth="2" strokeLinecap="round" />
    </g>
  );
}
