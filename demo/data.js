export const DURATION = 27;
export const STAGES = [
  {
    at: 5,
    end: 7.5,
    title: "Calibration",
    heading: "Calibrate the array.",
    text: "The phones settle into a shared time reference. Every position becomes part of the picture.",
    status: "SYNCHRONIZING DIRECT PATHS",
  },
  {
    at: 7.5,
    end: 12,
    title: "Impulse response",
    heading: "Listen for returns.",
    text: "A gentle sweep leaves the hub. Each phone listens as sound moves through the room.",
    status: "EMITTING A GENTLE SWEEP",
  },
  {
    at: 12,
    end: 14,
    title: "Candidate evidence",
    heading: "A field of possibilities.",
    text: "Three scanning beams trace the floor, walls, and ceiling. The structure forms before the details.",
    status: "TRACING ROOM BOUNDARIES",
  },
  {
    at: 14,
    end: 16,
    title: "Association",
    heading: "Evidence finds a surface.",
    text: "Compatible returns join into continuous walls. The room boundary becomes one coherent structure.",
    status: "FORMING CONTINUOUS WALLS",
  },
  {
    at: 16,
    end: 18,
    title: "Image sources",
    heading: "Locate the image source.",
    text: "With the room boundary established, three views trace the positions of furniture and fixtures.",
    status: "LOCATING ROOM OBJECTS",
  },
  {
    at: 18,
    end: 20.5,
    title: "Plane recovery",
    heading: "A plane from a reflection.",
    text: "Tables, chairs, and fixtures form row by row inside the completed room boundary.",
    status: "BUILDING OBJECT GEOMETRY",
  },
  {
    at: 20.5,
    end: 22.5,
    title: "Joint refinement",
    heading: "Every view adds information.",
    text: "Surface finishes resolve across the geometry. Roughness and reflectivity give each object its character.",
    status: "RESOLVING SURFACE MATERIALS",
  },
  {
    at: 22.5,
    end: 24.5,
    title: "Validation",
    heading: "Bring the evidence together.",
    text: "Estimated colors settle over the materials. The final model retains its original surface palette.",
    status: "RESTORING SURFACE COLOR",
  },
  {
    at: 24.5,
    end: 27,
    title: "Room reveal",
    heading: "The room comes together.",
    text: "The original room, down to its details. Explore the model and its illustrative surface estimates.",
    status: "REVEALING YOUR ROOM",
  },
];
export function stageAt(t) {
  return t < 5
    ? -1
    : STAGES.findIndex((s) => t >= s.at && t < s.end) === -1
      ? 8
      : STAGES.findIndex((s) => t >= s.at && t < s.end);
}
export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const smooth = (x) => {
  x = clamp(x);
  return x * x * (3 - 2 * x);
};
export function seeded(seed) {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
export function direction(a) {
  return [
    "Top",
    "Upper right",
    "Right",
    "Lower right",
    "Bottom",
    "Lower left",
    "Left",
    "Upper left",
  ][Math.round(a / 45) % 8];
}
export function makeEchoes(seed, count) {
  const r = seeded(seed);
  return Array.from({ length: count }, (_, i) => {
    const n = 5 + Math.floor(r() * 5);
    return Array.from({ length: n }, (_, j) => {
      const angle = Math.round(r() * 359);
      return {
        id: j + 1,
        angle,
        uncertainty: 10,
        direction: direction(angle),
        delay: Math.round((8 + j * 8 + r() * 5) * 10) / 10,
        amplitude: 0.4 + r() * 0.6,
        confidence: r() > 0.5 ? "HIGH" : "MEDIUM",
      };
    });
  });
}
export function confidenceFor(name) {
  let h = 0;
  for (const c of name) h = (h * 31 + c.charCodeAt(0)) | 0;
  const r = seeded(h);
  return {
    material: r() > 0.65 ? "HIGH" : "MEDIUM",
    color: r() > 0.25 ? "HIGH" : "MEDIUM",
    geometry: r() > 0.25 ? "HIGH" : "MEDIUM",
  };
}
