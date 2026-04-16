export type SkillLevel = "Beginner" | "Intermediate" | "Advanced";

export const SKILL_LEVELS = ["Beginner", "Intermediate", "Advanced"] as const;

export const ALL_SKILLS: string[] = [
  "Python",
  "JavaScript",
  "React",
  "FastAPI",
  "SQL",
  "PyTorch",
  "Figma",
  "Docker",
  "Kubernetes",
  "TypeScript",
  "HTML",
  "CSS",
  "Tailwind CSS",
  "Node.js",
  "Django",
  "C++",
  "Java",
  "Go",
  "Rust",
  "System Design"
];

export interface Skill {
  name: string;
  level: SkillLevel;
}

export interface Profile {
  skills: Skill[];
}