import {BrowserRouter, Route, Routes} from "react-router-dom"
import { AuthPage, Onboarding, RecommendationPage, RegistrationPage } from "../pages";
import { ProtectedRoute } from "./utils/protected_route";

export const RouterComponent = () => {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<ProtectedRoute><Onboarding/></ProtectedRoute>}/>
                <Route path="/home" element={<ProtectedRoute><RecommendationPage/></ProtectedRoute>}/>
                <Route path="/auth" element={<AuthPage/>}></Route>
                <Route path="/register" element={<RegistrationPage/>}></Route>
                <Route path="/registration" element={<RegistrationPage/>}></Route>
            </Routes>
        </BrowserRouter>
    );
}
