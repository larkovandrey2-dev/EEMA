import { Navigate } from "react-router-dom"
import { auth } from "../../shared/api/auth"
import { PropsWithChildren } from "react"

export const ProtectedRoute = ({ children }: PropsWithChildren) => {
    if (!auth.isLoggedIn()) {
        return <Navigate to="/auth" replace />
    }
    return <>{children}</>
}