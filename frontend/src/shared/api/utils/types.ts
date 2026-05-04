import { SkillLevel } from "../../../features/skill-group/utils/types"

export type AuthParams = {
  email: string
  password: string
}

export type LoginResponse = {
  status: string
  access_token: string
  refresh_token: string
  token_type: string
}

export type RegisterResponse = {
    status: string
    message: string
    user_id: string
}

export type RefreshResponse = {
  status: string
  access_token: string
  refresh_token: string
  token_type: string
}

export type ProfileParams = {
  skills: Record<string, string>
  learning_goals: string[]
  time_per_week: "low" | "medium" | "high"
}

export type Course = {
  id: number;
  title: string;
  url: string;
  stepik_id: number;

  difficulty: "easy" | "normal" | "hard" | null;
  is_paid: boolean;
  price: number | null;

  learners_count: number;
  rating: number
  similarity: number

  summary: string
  tags: string[]

  updated_at: string
};

export type BaselineResponse = {
  strategy: string;
  topics_used: string[];
  results_count: number;
  courses: Course[];
};

export type ProfileParseResponse = {
  status: string;
  data: {
    skills: Record<string, SkillLevel>;
    learning_goals: string[];
  };
};
export type ProfileParseParams = {
  text: string
}

export interface AdvancedRecommendationsResponse {
  strategy: string
  search_query: string
  main_results: Course[]
  ml_enrichment: MlEnrichment
}

export type Markov = {
  difficulty: "normal";
  id: number;
  learners_count: number;
  markov_reason: string;
  tags: string[];
  title: string;
  url: string;
};

export interface MlEnrichment {
  anchor_course_title: string
  cluster_neighbors: Course[]
  markov_roadmap: Markov[]
}