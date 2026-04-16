import { $api } from "./utils/axios"
import { BaselineResponse, ProfileParams, ProfileParseParams, ProfileParseResponse } from "./utils/types"

class Profile{
    updateProfile = async (profileData: ProfileParams) => {
        const res = await $api.post("/api/users/profile", profileData)
        const data = res.data
        return data
    }

    parseSkills = async (description: string) => {
        const res = await $api.post("/api/users/parse-skills", { text: description || "nothing" } as ProfileParseParams)
        const data: ProfileParseResponse = res.data
        return data
    }

    getBaseline = async () => {
        const res = await $api.get("/api/courses/recommend/baseline")
        const data: BaselineResponse = res.data
        return data
    }
}
export const profileApi = new Profile()