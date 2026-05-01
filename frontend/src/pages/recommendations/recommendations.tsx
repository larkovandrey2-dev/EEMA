import { useNavigate, Link } from "react-router-dom";
import { CourseBlock } from "../../features";
import { auth } from "../../shared/api/auth";
import "./recommendations.css";

const RecommendationPage = () => {
    const navigate = useNavigate();

    return (
        <div className="page-container">
            <header className="page-header">
                <div className="header-info">
                    <h1 className="page-title">Рекомендации для вас</h1>
                    <p className="page-subtitle">Подборка курсов на основе ваших навыков и интересов</p>
                </div>

                <div className="header-actions">

                    <Link to="/catalog" className="temp-button primary-button">
                        Весь каталог
                    </Link>

                    <button className="temp-button" onClick={() => navigate("/")}>
                        Профиль
                    </button>
                    <button className="temp-button logout-btn" onClick={auth.logout}>
                        Выйти
                    </button>
                </div>
            </header>

            <main className="page-content">
                <CourseBlock />
            </main>
        </div>
    );
};

export default RecommendationPage;