import { useNavigate } from "react-router-dom"
import { CourseBlock } from "../../features"
import { auth } from "../../shared/api/auth"
import "./recommendations.css"

const RecommendationPage = () => {
    const navigate = useNavigate()
    return (
        <div>
            <button className="temp-button" onClick={auth.logout}>Выйти из аккаунта</button>
            <button className="temp-button" onClick={() => navigate("/")}>Профиль</button>
            <CourseBlock></CourseBlock>
        </div>
    )
}
export default RecommendationPage