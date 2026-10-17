import {
    getCurrentUser as sdkGetCurrentUser,
    login as sdkLogin,
} from '@/client/sdk.gen'
import type { LoginResponse, MeResponse, UserRead } from '@/client/types.gen'
import type { AuthUser } from '@/stores/authStore'

function toAuthUser(payload: LoginResponse | MeResponse): AuthUser {
    const user = payload.user as UserRead
    return {
        id: user.id,
        username: user.username,
        displayName: user.display_name,
        permissionTags: payload.permission_tags ?? [],
        isAdmin: payload.is_admin,
        roleNames: user.roles?.map((r) => r.name) ?? []
    }
}

// 登录结果承载体
export interface LoginResult {
    token: string
    user: AuthUser
}

/** 登录 */
export async function login(username: string, password: string): Promise<LoginResult> {
    const { data } = await sdkLogin( { body: {username, password} })
    if(!data) {
        throw new Error("登录失败")
    }
    return { token: data.access_token, user: toAuthUser(data) }
}

/** 获取当前用户信息 */
export async function fetchCurrentUser(): Promise<AuthUser> {
    const {data} = await sdkGetCurrentUser()
    if (!data) throw new Error("获取用户信息失败")
    return toAuthUser(data)
}

