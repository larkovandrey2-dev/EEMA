import { $api } from "./utils/axios"
import { BaselineResponse, ProfileParams, ProfileParseParams, ProfileParseResponse } from "./utils/types"

class Profile{
    updateProfile = async (profileData: ProfileParams) => {
        const res = await $api.post("/api/users/profile", profileData)
        const data = res.data
        return data
    }

    getProfile = async () => {
        const res = await $api.get("/api/users/profile")
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

    getAdvancedRecommendations = async (query: string, limit: number = 5) => {
        const res = await $api.post("/api/courses/recommend/advanced", { "query": query, "limit": limit })
        const data = res.data
        return data
    }

    likeCourse = async (course_id: number) => {
        const res = await $api.post(`/api/courses/${course_id}/like`)
        const data = res.data
        return data
    }
    unlikeCourse = async (course_id: number) => {
        const res = await $api.delete(`/api/courses/${course_id}/like`)
        const data = res.data
        return data
    }
}
export const profileApi = new Profile()