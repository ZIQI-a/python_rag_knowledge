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
    user: {id: string; name: string} | null
    token: string | null
    ready: boolean
    setAuth: (user: AuthState['user'], token: string | null) => void
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
    ready: false,

    setAuth: (user, token) => {
        localStorage.setItem(TOKEN_KEY, token)
        localStorage.setItem(USER_KEY, JSON.stringify(user))
        set({ token, user })
    },

    setUser: (user) => {
        localStorage.setItem(USER_KEY, JSON.stringify(user))
        set({ user })
    },
    logout: () => {
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem(USER_KEY)
        set({user: null, token: null})
    },
    hasToken: () => Boolean(get().token),
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

