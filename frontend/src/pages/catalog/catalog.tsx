import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import './catalog.css';
import '../../features/course-block/ui/course-unit.css';

interface Course {
    id: number | string;
    title: string;
    url: string;
    difficulty: string | null;
    learners_count: number;
    rating: number;
    is_paid: boolean;
    price: number;
    summary?: string;
}

const sortOptions = ["Популярность", "Рейтинг", "Новинки"];
const difficulties = ["Новичок", "Средний", "Профи"];
const diffMap: Record<string, string> = { "Новичок": "easy", "Средний": "normal", "Профи": "hard" };
const sortMap: Record<string, string> = { "Популярность": "popular", "Рейтинг": "rating", "Новинки": "new" };

export const CatalogPage = () => {
    const [courses, setCourses] = useState<Course[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [meta, setMeta] = useState({ totalPages: 1, totalItems: 0 });
    const [lastUpdate, setLastUpdate] = useState<string>("Загрузка...");

    const [currentPage, setCurrentPage] = useState(1);
    const [searchQuery, setSearchQuery] = useState("");
    const [selectedSort, setSelectedSort] = useState("Популярность");
    const [selectedDiffs, setSelectedDiffs] = useState<string[]>([]);

    const fetchCourses = useCallback(async () => {
        setIsLoading(true);
        try {
            const params = new URLSearchParams({
                page: String(currentPage),
                size: '32',
                sort_by: sortMap[selectedSort],
            });

            if (searchQuery) params.append('search', searchQuery);


            if (selectedDiffs.length > 0) {
                params.append('difficulty', diffMap[selectedDiffs[selectedDiffs.length - 1]]);
            }

            const response = await axios.get(`http://127.0.0.1:8000/api/courses/catalog?${params.toString()}`);
            setCourses(response.data.courses || []);
             setLastUpdate(response.data.update_date || "Данные отсутствуют");
            setMeta({
                totalPages: response.data.meta.total_pages,
                totalItems: response.data.meta.total_items
            });
        } catch (e) {
            console.error(e);
        } finally {
            setIsLoading(false);
        }
    }, [currentPage, selectedSort, selectedDiffs, searchQuery]);

    useEffect(() => {
        const timer = setTimeout(fetchCourses, 400);
        return () => clearTimeout(timer);
    }, [fetchCourses]);

    const toggleDiff = (diff: string) => {
        setSelectedDiffs(prev =>
            prev.includes(diff) ? prev.filter(d => d !== diff) : [...prev, diff]
        );
        setCurrentPage(1);
    };

    const getDifficultyClass = (diff: string | null) => {
        switch (diff?.toLowerCase()) {
            case 'easy': return 'beginner';
            case 'normal': return 'intermediate';
            case 'hard': return 'advanced';
            default: return 'unknown';
        }
    };

    return (
        <div className="page-container catalog-page">
            <header className="page-header">
                <h1 className="page-title">Каталог курсов 📚</h1>
                <p className="page-subtitle">Найдено курсов: {meta.totalItems}</p>
                <div className="db-status">
                        <span className="status-dot"></span>
                        <p className="page-subtitle">База обновлена: {lastUpdate}</p>
                </div>
                <div className="header-stats">
                    Найдено: <strong>{meta.totalItems}</strong>
                </div>
            </header>

            <section className="filters-section">

                <div className="search-box">
                    <input
                        type="text"
                        placeholder="Поиск по названию..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                </div>

                <div className="filter-row">
                    <div className="filter-group">
                        <span className="filter-label">Сортировка:</span>
                        <div className="chips-group">
                            {sortOptions.map(opt => (
                                <button
                                    key={opt}
                                    className={`chip ${selectedSort === opt ? 'active' : ''}`}
                                    onClick={() => setSelectedSort(opt)}
                                >
                                    {opt}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="filter-group">
                        <span className="filter-label">Уровень:</span>
                        <div className="chips-group">
                            {difficulties.map(diff => (
                                <button
                                    key={diff}
                                    className={`chip chip-checkbox ${selectedDiffs.includes(diff) ? 'active' : ''}`}
                                    onClick={() => toggleDiff(diff)}
                                >
                                    {selectedDiffs.includes(diff) && <span className="check-icon">✓</span>}
                                    {diff}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>
            </section>

            <main className="catalog-content">
                {isLoading ? (
                    <div className="loader">Загружаем знания...</div>
                ) : (
                    <div className="course-grid">
                        {courses.map(course => (
                            <a key={course.id} href={course.url} target="_blank" rel="noreferrer" className="courseUnit">
                                <div className="courseUnit__top">
                                    <span className={`courseUnit__badge ${getDifficultyClass(course.difficulty)}`}>
                                        {(course.difficulty || 'UNKNOWN').toUpperCase()}
                                    </span>
                                    <span className={course.is_paid ? "paid" : "free"}>
                                        {course.is_paid ? `${course.price} ₽` : "FREE"}
                                    </span>
                                </div>
                                <h3 className="courseUnit__title">{course.title}</h3>
                                <div className="courseUnit__meta">
                                    <span>👥 {course.learners_count?.toLocaleString()}</span>
                                    <span>⭐ {course.rating || 4.5}</span>
                                </div>
                            </a>
                        ))}
                    </div>
                )}
            </main>

            {meta.totalPages > 1 && (
                <div className="pagination">
                    <button className="temp-button" disabled={currentPage === 1} onClick={() => setCurrentPage(p => p - 1)}>←</button>
                    <span className="page-num">{currentPage} / {meta.totalPages}</span>
                    <button className="temp-button" disabled={currentPage === meta.totalPages} onClick={() => setCurrentPage(p => p + 1)}>→</button>
                </div>
            )}
        </div>
    );
};