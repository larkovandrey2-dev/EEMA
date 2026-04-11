import React from "react"
import { auth } from "../../shared/api/auth";
import { useNavigate } from "react-router-dom"

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
    <div>
        <form onSubmit={handleSubmit}>
            <input type="text" placeholder="email" 
                value={email} onChange={(e) => setEmail(e.target.value)} />
            <input type="password" placeholder="password" 
                value={password} onChange={(e) => setPassword(e.target.value)} />
            <button type="submit">Войти</button>
        </form>
    </div>
    );
}
export default RegistrationPage