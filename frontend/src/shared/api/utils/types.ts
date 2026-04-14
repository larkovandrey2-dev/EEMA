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
  difficulty: "easy" | "normal" | "hard" | null;
  is_paid: boolean;
  price: number | null;
  learners_count: number;
};

export type BaselineResponse = {
  strategy: string;
  topics_used: string[];
  results_count: number;
  courses: Course[];
};