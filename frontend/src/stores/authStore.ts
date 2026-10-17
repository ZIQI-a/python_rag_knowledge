import {create} from "zustand";

const TOKEN_KEY = 'rag-kb.auth.token'
const USER_KEY = 'rag-kb.auth.user'

// 用户信息
export interface AuthUser{
    id: string
    username: string
    displayName: string
    permissionTags: string[]
    isAdmin: boolean
    roleNames: string[]
}

interface AuthState{
    token: string | null
    user: AuthUser | null
    ready: boolean
    setAuth: (token: string, user: AuthUser) => void
    setUser: (user: AuthUser) => void
    logout: () => void
    hasToken: () => boolean
    hydrate: () => void
}

// 从本地存储中加载用户信息
function loadUser(): AuthUser | null {
    const raw = localStorage.getItem(USER_KEY)
    if (!raw) return null
    try {
        return JSON.parse(raw) as AuthUser
    } catch {
        return null
    }
}

export const useAuthStore = create<AuthState>((set, get) => ({
    token: null,
    user: null,
    ready: false, // 是否已加载完成

    //  设置用户信息和token
    setAuth: (token, user) => {
        localStorage.setItem(TOKEN_KEY, token)
        localStorage.setItem(USER_KEY, JSON.stringify(user))
        set({ token, user })
    },
    // 设置用户信息
    setUser: (user) => {
        localStorage.setItem(USER_KEY, JSON.stringify(user))
        set({ user })
    },
    // 登出
    logout: () => {
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem(USER_KEY)
        set({user: null, token: null})
    },
    // 判断是否有token
    hasToken: () => Boolean(get().token),
    // 加载用户信息
    hydrate: () => {
        const token = localStorage.getItem(TOKEN_KEY)
        const user = loadUser()
        set({ token, user, ready: true })
    }
}))

/** 给SSE拦截器用，直接读取最新token */
export function getAuthToken(): string | null {
    return useAuthStore.getState().token
}

