import { $api } from "./utils/axios"
import { BaselineResponse, ProfileParams } from "./utils/types"

class Profile{
    updateProfile = async (profileData: ProfileParams) => {
        const res = await $api.post("/api/users/profile", profileData)
        return res.data
    }

    getBaseline = async () => {
        const res = await $api.get("/api/courses/recommend/baseline")
        const data: BaselineResponse = res.data
        return data
    }
}
export const profileApi = new Profile()