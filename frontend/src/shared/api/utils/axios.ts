import { baseurl } from "../../config/config"
import axios from "axios"
import { tokenStorage } from "./token"
import { auth } from "../auth"

import "axios"

declare module "axios" {
  export interface AxiosRequestConfig {
    skipAuthRefresh?: boolean
  }
}

export const $api = axios.create({
  baseURL: baseurl,
  withCredentials: true,
})

let isRefreshing = false
let queue: any[] = []

$api.interceptors.request.use((config) => {
  const token = tokenStorage.getAccess()

  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  return config
})

$api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status !== 401) {
      return Promise.reject(error)
    }

    if (originalRequest?.skipAuthRefresh) {
      return Promise.reject(error)
    }

    if (isRefreshing) {
      return new Promise((resolve) => {
        queue.push((token: string) => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          resolve($api(originalRequest))
        })
      })
    }

    isRefreshing = true

    try {
      const newToken = await auth.refreshAccessToken()

      tokenStorage.setAccess(newToken)

      queue.forEach((cb) => cb(newToken))
      queue = []

      originalRequest.headers.Authorization = `Bearer ${newToken}`

      return $api(originalRequest)
    } catch (e) {
      auth.logout()

      window.location.href = "/auth"

      return new Promise(() => {})
    } finally {
      isRefreshing = false
    }
  }
)