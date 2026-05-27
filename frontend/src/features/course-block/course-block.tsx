import { profileApi } from "../../shared"
import { useEffect, useState } from "react"
import { CourseGroup } from "./ui/course-group"
import { CourseUnit } from "../../shared";
import { AdvancedRecommendationsResponse } from "../../shared/api/utils/types";
import "./course-block.css"
import MarkovCourse from "./ui/markov";

export const CourseBlock = () => {
    const [recommendations, setRecommendations] = useState<AdvancedRecommendationsResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [filled, setFilled] = useState(false);
    const [text, setText] = useState("");

    const fetchData = async () => {
            try {
                const res = await profileApi.getAdvancedRecommendations(text)
                setRecommendations(res)
                console.log(res)
            } catch (e) {
                console.error("Ошибка при получении рекомендаций:", e);
                
            } finally {
                setLoading(false)
            }
        }
    
    const handleClick = () => {
        setLoading(true)
        setFilled(true)
        fetchData();
    }

    return (
        <div>
            <div className="search-bar">
                <div className="search-input-wrapper">
                    <span className="icon">✨</span>
                    <input
                      value={text}
                      onChange={(e) => {setText(e.target.value)}}
                      type="text"
                      placeholder="Введите запрос..."
                        />
                    </div>
                <button className="search-button" onClick={handleClick} disabled={!text}>Найти рекомендации</button>
            </div>
            {filled ? loading ? <p>Загрузка...</p> : recommendations?.main_results && recommendations.main_results.length ? <div className="sections-grid">
                <div className="course-group-wrapper">
                    <p className="course-group-title">Топ-5 курсов</p>
                    <CourseGroup courses={recommendations?.main_results}></CourseGroup></div>
                <div className="course-group-wrapper">
                    <p className="course-group-title">Траектория обучения</p>
                    {recommendations?.ml_enrichment.markov_roadmap.map((markov, index) => (
                    <MarkovCourse key={index} markov={markov} id={index + 1} />
                ))}</div>
                <div className="course-group-wrapper">
                    <p className="course-group-title">Похожие курсы</p>
                    {recommendations?.ml_enrichment.cluster_neighbors.map((course, index) => (
                    <CourseUnit key={index} id={course.cluster_id} title={course.title} url={course.url} difficulty={course.difficulty} is_paid={course.is_paid} price={course.price} learners_count={course.learners_count} stepik_id={course.stepik_id} rating={course.rating} similarity={course.similarity} summary={course.summary} updated_at={course.updated_at} tags={course.tags} />
                ))}</div>
                </div>: 
                <p>Нет рекомендаций для отображения</p>: <p>Введите запрос</p>}
        </div>
    );
}