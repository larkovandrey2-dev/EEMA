import { $api } from "./utils/axios"
import { tokenStorage } from "./utils/token"
import { AuthParams, LoginResponse, RegisterResponse, RefreshResponse } from "./utils/types"


class Auth{
    refreshAccessToken = async () => {
        const refresh = tokenStorage.getRefresh()

        const res = await $api.post("/api/auth/refresh", {
            refresh_token: refresh,
        }, { skipAuthRefresh: true })

        const newAccess: RefreshResponse = res.data
        tokenStorage.setAccess(newAccess.access_token)
        tokenStorage.setRefresh(newAccess.refresh_token)
        return newAccess.access_token
    }

    login = async ({email, password}: AuthParams) => {
        const res = await $api.post("/api/auth/login", {
            email,
            password
        }, { skipAuthRefresh: true })

        const data: LoginResponse = res.data

        tokenStorage.setAccess(data.access_token)
        tokenStorage.setRefresh(data.refresh_token)

        return data
        
    }

    register = async ({email, password}: AuthParams) => {
        const res = await $api.post("/api/auth/register", {
            email,
            password
        }, { skipAuthRefresh: true })

        const data: RegisterResponse = res.data

        return data
        
    }

    logout = () => {
        tokenStorage.removeAccess()
        tokenStorage.removeRefresh()
        window.location.href = "/auth"
    }

    isLoggedIn = () => {
        return !!tokenStorage.getAccess() && !!tokenStorage.getRefresh()
    }
}

export const auth = new Auth()