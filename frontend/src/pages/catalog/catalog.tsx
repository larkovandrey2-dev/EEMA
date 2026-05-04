import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import './catalog.css';

interface Course {
    id: number | string;
    title: string;
    url: string;
    difficulty: string | null;
    learners_count: number;
    rating: number;
    is_paid: boolean;
    price: number;
}

const sortOptions = ["Популярность", "Рейтинг", "Новинки"];
const difficulties = ["Новичок", "Средний", "Профи"];
const diffMap: Record<string, string> = { "Новичок": "easy", "Средний": "normal", "Профи": "hard" };
const sortMap: Record<string, string> = { "Популярность": "popular", "Рейтинг": "rating", "Новинки": "new" };

export const CatalogPage = () => {

    const [courses, setCourses] = useState<Course[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [lastUpdate, setLastUpdate] = useState<string>("Загрузка...");
    const [meta, setMeta] = useState({ totalPages: 1, totalItems: 0 });

    const [currentPage, setCurrentPage] = useState(1);
    const [inputPage, setInputPage] = useState("1");
    const [searchQuery, setSearchQuery] = useState("");
    const [selectedSort, setSelectedSort] = useState("Популярность");
    const [selectedDiffs, setSelectedDiffs] = useState<string[]>([]);

    const getDifficultyClass = (diff: string | null) => {
        switch (diff?.toLowerCase()) {
            case 'easy': return 'beginner';
            case 'normal': return 'intermediate';
            case 'hard': return 'advanced';
            default: return 'unknown';
        }
    };

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
            setLastUpdate(response.data.update_date || "Неизвестно");
            setMeta({
                totalPages: response.data.meta?.total_pages || 1,
                totalItems: response.data.meta?.total_items || 0
            });
        } catch (e) {
            console.error(e);
            setLastUpdate("Ошибка подключения");
        } finally {
            setIsLoading(false);
        }
    }, [currentPage, selectedSort, selectedDiffs, searchQuery]);

    useEffect(() => {
        const timer = setTimeout(fetchCourses, 400);
        return () => clearTimeout(timer);
    }, [fetchCourses]);

    useEffect(() => {
        setCurrentPage(1);
    }, [selectedSort, selectedDiffs, searchQuery]);

    useEffect(() => {
        setInputPage(String(currentPage));
    }, [currentPage]);

    const toggleDiff = (diff: string) => {
        setSelectedDiffs(prev =>
            prev.includes(diff) ? prev.filter(d => d !== diff) : [...prev, diff]
        );
    };

    const handlePageSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        const num = parseInt(inputPage);
        if (!isNaN(num) && num >= 1 && num <= meta.totalPages) {
            setCurrentPage(num);
            window.scrollTo({ top: 0, behavior: 'smooth' });
        } else {
            setInputPage(String(currentPage));
        }
    };

    return (
        <div className="page-container catalog-page">
            <header className="page-header catalog-header">
                <div className="header-left">
                    <Link to="/home" className="back-link">← Назад к рекомендациям</Link>
                    <div className="header-info">
                        <h1 className="page-title">Каталог курсов 📚</h1>
                        <div className="db-status">
                            <span className="status-dot"></span>
                            <p className="page-subtitle">База обновлена: {lastUpdate}</p>
                        </div>
                    </div>
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
                ) : courses.length === 0 ? (
                    <div className="empty-state">По вашему запросу ничего не найдено 😔</div>
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
                                <div className="courseUnit__meta" style={{marginTop: 'auto', paddingTop: '15px'}}>
                                    <span>👥 {course.learners_count?.toLocaleString()}</span>
                                    <span>⭐ {course.rating || 4.5}</span>
                                </div>
                            </a>
                        ))}
                    </div>
                )}
            </main>

            {!isLoading && meta.totalPages > 1 && (
                <div className="pagination">
                    <button className="temp-button" disabled={currentPage <= 1} onClick={() => setCurrentPage(p => p - 1)}>←</button>

                    <form className="page-input-form" onSubmit={handlePageSubmit}>
                        <span>Страница</span>
                        <input
                            type="number"
                            className="page-number-input"
                            value={inputPage}
                            onChange={(e) => setInputPage(e.target.value)}
                            onBlur={handlePageSubmit}
                        />
                        <span>из {meta.totalPages}</span>
                    </form>

                    <button className="temp-button primary-button" disabled={currentPage >= meta.totalPages} onClick={() => setCurrentPage(p => p + 1)}>→</button>
                </div>
            )}
        </div>
    );
};