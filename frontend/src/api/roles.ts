import {type QueryClient, useMutation, useQuery, useQueryClient} from "@tanstack/react-query";
import {
    createRole as sdkCreateRole,
    deleteRole as sdkDeleteRole,
    listRoles as sdkListRoles, type RoleCreate, type RoleUpdate,
    updateRole as sdkUpdateRole,
} from "@/client";
import {currentUserKey, rolesListKey} from "@/api/queryKeys.ts";

/** 角色清单，用户页的下拉框和 11.4.3 的角色页共用 */
export function useRoles() {
    return useQuery({
        queryKey: rolesListKey,
        // 角色改动很少，5 分钟内不重复请求
        staleTime: 5 * 60 * 1000,
        queryFn: async () => (await sdkListRoles()).data!,
    })
}

/** 角色变化后需要刷新的3个缓存 */
function invalidateAfterRoleChange(queryClient: QueryClient) {
    queryClient.invalidateQueries({ queryKey: rolesListKey })
    queryClient.invalidateQueries({ queryKey: ['users'] })
    queryClient.invalidateQueries({ queryKey: currentUserKey })
}

/** 新建角色 */
export function useCreateRole() {
    const queryClient = useQueryClient()
    return useMutation({
        mutationFn: async (body: RoleCreate) => (await sdkCreateRole({ body })).data!,
        onSuccess: () => invalidateAfterRoleChange(queryClient),
    })
}

/** 修改描述 / 权限标签（name 不允许改） */
export function useUpdateRole() {
    const queryClient = useQueryClient()
    return useMutation({
        mutationFn: async (params: { roleId: string; body: RoleUpdate }) =>
            (await sdkUpdateRole({ path: { role_id: params.roleId }, body: params.body })).data!,
        onSuccess: () => invalidateAfterRoleChange(queryClient),
    })
}

/** 删除角色（内置角色后端会拒绝） */
export function useDeleteRole() {
    const queryClient = useQueryClient()
    return useMutation({
        // deleteRole 返回 204，没有响应体
        mutationFn: async (roleId: string) => {
            await sdkDeleteRole({ path: { role_id: roleId } })
        },
        onSuccess: () => invalidateAfterRoleChange(queryClient),
    })
}
