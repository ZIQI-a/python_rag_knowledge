/** 用户管理相关内容 */
import {useMutation, useQuery, useQueryClient} from "@tanstack/react-query";
import {
    assignUserRoles as sdkAssignUserRoles,
    createUser as sdkCreateUser,
    deleteUser as sdkDeleteUser,
    listUsers as sdkListUsers,
    updateUser as sdkUpdateUser,
} from "@/client";
import type {UserCreate, UserUpdate} from "@/client";
import {currentUserKey, usersListKey} from "@/api/queryKeys.ts";

/** 用户列表（分页） */
export function useUsers(page: number, pageSize: number) {
    return useQuery({
        // key 里带上分页参数：换页就是换一份缓存
        queryKey: usersListKey(page, pageSize),
        queryFn: async () =>
            (await sdkListUsers({ query: { page, page_size: pageSize } })).data!,
        // 翻页时先沿用上一页的数据，避免表格闪一下空白
        placeholderData: (prev) => prev,
    })
}

/** 新建用户 */
export function useCreateUser() {
    const queryClient = useQueryClient()
    return useMutation({
        mutationFn: async (body: UserCreate) => (await sdkCreateUser({ body })).data!,
        onSuccess: () => {
            // ['users'] 是前缀，能一次匹配所有分页缓存
            queryClient.invalidateQueries({ queryKey: ['users'] })
        },
    })
}

/** 修改昵称 / 状态 / 密码 */
export function useUpdateUser() {
    const queryClient = useQueryClient()
    return useMutation({
        mutationFn: async (params: { userId: string; body: UserUpdate }) =>
            (await sdkUpdateUser({ path: { user_id: params.userId }, body: params.body })).data!,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['users'] })
            // 改的是自己时，顶栏昵称要跟着刷新
            queryClient.invalidateQueries({ queryKey: currentUserKey })
        },
    })
}

/** 分配角色 */
export function useAssignUserRoles() {
    const queryClient = useQueryClient()
    return useMutation({
        mutationFn: async (params: { userId: string; roleIds: string[] }) =>
            (
                await sdkAssignUserRoles({
                    path: { user_id: params.userId },
                    body: { role_ids: params.roleIds },
                })
            ).data!,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['users'] })
            queryClient.invalidateQueries({ queryKey: currentUserKey })
        },
    })
}

/** 删除用户 */
export function useDeleteUser() {
    const queryClient = useQueryClient()
    return useMutation({
        // deleteUser 返回 204，没有响应体，所以不取 .data
        mutationFn: async (userId: string) => {
            await sdkDeleteUser({ path: { user_id: userId } })
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['users'] })
        },
    })
}
