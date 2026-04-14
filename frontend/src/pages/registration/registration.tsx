import React from "react"
import { auth } from "../../shared/api/auth";
import { useNavigate } from "react-router-dom"
import "./registration.css"
import { ThemeButton } from "../../shared";

const RegistrationPage = () => {
    const [email, setEmail] = React.useState("")
    const [password, setPassword] = React.useState("")
    const navigate = useNavigate()

    const handleSubmit = async (event: React.FormEvent) => {
        event.preventDefault();
        try{
            await auth.register({email, password})
            await auth.login({email, password})
            navigate("/", { replace: true })
        } catch (e) {
            console.log("login error", e)
        }
    }
    return (
    <div className="auth-wrapper">
    <div className="auth-container">
        <div className="auth-top">
            <ThemeButton></ThemeButton>
        </div>
        <form onSubmit={handleSubmit} className="auth-form">
            <h2 className="auth-title">Регистрация</h2>

            <input
                className="auth-input"
                type="text"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
            />

            <input
                className="auth-input"
                type="password"
                placeholder="Пароль"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
            />      
            <button type="submit" className="auth-button">
                Зарегистрироваться
            </button>
            <button
            type="button"
            className="auth-switch"
            onClick={() => navigate('/auth')}
            >
            Авторизация
            </button>
        </form>
    </div>
    </div>
    );
}
export default RegistrationPage