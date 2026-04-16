const ACCESS = "access_token"
const REFRESH = "refresh_token"

export const tokenStorage = {
  getAccess: () => localStorage.getItem(ACCESS),
  setAccess: (t: string) => localStorage.setItem(ACCESS, t),
  removeAccess: () => localStorage.removeItem(ACCESS),

  getRefresh: () => localStorage.getItem(REFRESH),
  setRefresh: (t: string) => localStorage.setItem(REFRESH, t),
  removeRefresh: () => localStorage.removeItem(REFRESH),
}