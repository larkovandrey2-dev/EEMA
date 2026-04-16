import { BaselineResponse, profileApi } from "../../shared"
import { useEffect, useState } from "react"
import { CourseGroup } from "./ui/course-group"

export const CourseBlock = () => {
    const [baseline, setBaseline] = useState<BaselineResponse | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchBaseline = async () => {
        try {
            const data = await profileApi.getBaseline();
            setBaseline(data);
        } catch (e) {
            console.error("Ошибка:", e);
        } finally {
            setLoading(false);
        }
        };

        fetchBaseline();
    }, []);
    return (
        <div>
            {loading ? <p>Загрузка...</p> : !!baseline ? <CourseGroup courses={baseline?.courses}></CourseGroup>: <p>Нет рекомендаций для отображения</p>}
        </div>
    );
}