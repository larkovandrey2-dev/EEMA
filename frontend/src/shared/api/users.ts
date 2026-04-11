import { $api } from "./utils/axios"
import { ProfileParams } from "./utils/types"

class Profile{
    updateProfile = async (profileData: ProfileParams) => {
        const res = await $api.post("/api/users/profile", profileData)
        return res.data
    }
}
export const profileApi = new Profile()