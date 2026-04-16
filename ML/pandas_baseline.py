import pandas as pd


def get_pandas_baseline_recommendations(courses_df: pd.DataFrame, user_profile: dict, limit: int = 10) -> list:
    """
    Ожидаемые колонки в courses_df:
    - id (уникальный ID курса)
    - title (название)
    - tags (строка с тегами или список, например "python, web" или "['python', 'web']")
    - learners_count (число студентов/популярность)
    - difficulty (сложность: 'easy', 'normal', 'hard') - опционально
    """

    skills = user_profile.get("skills", {})
    goals = user_profile.get("learning_goals", [])

    difficulty_map = {
        "beginner": "easy",
        "medium": "normal",
        "hard": "hard"
    }

    recommended_courses = []
    seen_ids = set()

    def add_courses(filtered_df):
        """Вспомогательная функция для добавления курсов в результат"""
        for _, row in filtered_df.iterrows():
            if row['id'] not in seen_ids:
                seen_ids.add(row['id'])
                recommended_courses.append(row.to_dict())

    # ЭТАП 1: Ищем по ЦЕЛЯМ
    for goal in goals[:2]:
        mask_tag = courses_df['tags'].str.contains(goal, case=False, na=False)
        mask_diff = courses_df['difficulty'] == 'easy' if 'difficulty' in courses_df.columns else True
        top_goal_courses = courses_df[mask_tag & mask_diff].sort_values(by='learners_count', ascending=False).head(3)
        add_courses(top_goal_courses)

    #ЭТАП 2: Ищем по ТЕКУЩИМ НАВЫКАМ
    for skill_name, skill_level in list(skills.items())[:2]:
        target_diff = difficulty_map.get(skill_level.lower(), "easy")

        mask_tag = courses_df['tags'].str.contains(skill_name, case=False, na=False)
        mask_diff = courses_df['difficulty'] == target_diff if 'difficulty' in courses_df.columns else True

        top_skill_courses = courses_df[mask_tag & mask_diff].sort_values(by='learners_count', ascending=False).head(3)
        add_courses(top_skill_courses)

    #ЭТАП 3: Добиваем популярными курсами, если не набрали лимит
    if len(recommended_courses) < limit:
        mask_not_seen = ~courses_df['id'].isin(seen_ids)
        fallback_courses = courses_df[mask_not_seen].sort_values(by='learners_count', ascending=False).head(
            limit - len(recommended_courses))
        add_courses(fallback_courses)
    return recommended_courses[:limit]



if __name__ == "__main__":
    # 1. Создаем фейковый датафрейм
    data = [
        {"id": 1, "title": "Основы Python", "tags": "python, basics", "learners_count": 5000, "difficulty": "easy"},
        {"id": 2, "title": "Pro Python", "tags": "python, advanced", "learners_count": 2000, "difficulty": "hard"},
        {"id": 3, "title": "Введение в Data Science", "tags": "data science, pandas, python", "learners_count": 8000,
         "difficulty": "easy"},
        {"id": 4, "title": "Docker для новичков", "tags": "docker, devops", "learners_count": 3000,
         "difficulty": "easy"},
        {"id": 5, "title": "Сложный SQL", "tags": "sql, databases", "learners_count": 1500, "difficulty": "hard"},
        {"id": 6, "title": "HTML и CSS", "tags": "html, css, web", "learners_count": 10000, "difficulty": "easy"}
    ]
    df_courses = pd.DataFrame(data)

    # 2. Фейковый юзер
    user_profile = {
        "skills": {"SQL": "hard"},
        "learning_goals": ["Python", "Docker"]
    }

    # 3. Получаем рекомендации (Бейзлайн)
    recommendations = get_pandas_baseline_recommendations(df_courses, user_profile, limit=3)

    # 4. Вывод в консоль
    print(f"Профиль: {user_profile}\n")
    print("Рекомендации (Бейзлайн):")
    for r in recommendations:
        print(f" - [{r['difficulty']}] {r['title']} (Студентов: {r['learners_count']})")