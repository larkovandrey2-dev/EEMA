import {BrowserRouter, Route, Routes} from "react-router-dom"
import { AuthPage, Onboarding, RecommendationPage, RegistrationPage } from "../pages";
import { ProtectedRoute } from "./utils/protected_route";
import { CatalogPage } from '../pages/catalog/catalog';

export const RouterComponent = () => {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<ProtectedRoute><Onboarding/></ProtectedRoute>}/>
                <Route path="/home" element={<ProtectedRoute><RecommendationPage/></ProtectedRoute>}/>
                <Route path="/auth" element={<AuthPage/>}></Route>
                <Route path="/register" element={<RegistrationPage/>}></Route>
                <Route path="/catalog" element={<CatalogPage />}></Route>
            </Routes>
        </BrowserRouter>
    );
}