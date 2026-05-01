import time

from app.core.database import supabase
from services.llm_request import ask_yagpt
from collections import Counter
import json
def get_golden_tags(min_occur:int = 3, max_tags:int = 200):

    resp = supabase.table("courses").select("tags").execute()
    all_tags = []
    for row in resp.data:
        tags = row.get("tags")
        if tags:
            all_tags.extend([t.strip() for t in tags])
    tag_counts = Counter(all_tags)
    golden_tags = []
    for tag, count in tag_counts.most_common(max_tags):
        if count >= min_occur:
            golden_tags.append(tag)
    return golden_tags


def generate_transition_matrix(tags_batch: list, all_golden_tags: list):
    golden_dict_str = ", ".join(all_golden_tags)
    batch_str = ", ".join(tags_batch)
    system_prompt = f"""
        Ты Senior IT Ментор и Data Scientist. Твоя задача — построить Марковскую цепь образовательных траекторий.
        Я дам тебе несколько тегов (навыков/технологий). Для каждого из них выбери от 2 до 4 тегов, которые логично изучать СЛЕДУЮЩИМИ.

        ЖЕСТКИЕ ПРАВИЛА:
        1. Следующие шаги выбирай СТРОГО из этого разрешенного словаря: [{golden_dict_str}]. Не придумывай свои теги!
        2. Распредели вероятность перехода (сумма вероятностей для одного тега должна быть ровно 1.0).
        3. Не зацикливай тег на самого себя.
        4. ВЕРНИ ТОЛЬКО ЧИСТЫЙ JSON. Никакого текста, никаких маркдаун-кавычек (```json).

        Формат ответа:
        {{
            "ТекущийТег1": {{"СледующийТегA": 0.6, "СледующийТегB": 0.4}},
            "ТекущийТег2": {{"СледующийТегC": 0.7, "СледующийТегD": 0.3}}
        }}
        """

    user_text = f"Сгенерируй следующие шаги для этих тегов: [{batch_str}]"
    try:
        resp = ask_yagpt(system_prompt=system_prompt, user_text=user_text,temperature=0.0)
        clean_result = resp.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_result)
    except Exception as e:
        print(e)
        return {}


def build_markov_matrix():
    golden_tags = get_golden_tags(min_occur=3, max_tags=250)
    print(golden_tags)
    final_markov_matrix = {}
    batch_size = 5
    for i in range(0,len(golden_tags),batch_size):
        batch = golden_tags[i:i+batch_size]
        print(f"{i}/{i+batch_size+1}: {batch}")
        transition_matrix = generate_transition_matrix(batch, golden_tags)
        if transition_matrix:
            final_markov_matrix.update(transition_matrix)
            print("Successfully generated transition matrix batch")
        time.sleep(1)
    with open("markov_matrix.json", "w") as f:
        json.dump(final_markov_matrix, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    build_markov_matrix()
