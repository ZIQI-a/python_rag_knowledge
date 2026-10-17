import {useQuery} from "@tanstack/react-query";
import {listRoles as sdkListRoles} from "@/client";
import {rolesListKey} from "@/api/queryKeys.ts";

/** 角色清单，用户页的下拉框和 11.4.3 的角色页共用 */
export function useRoles() {
    return useQuery({
        queryKey: rolesListKey,
        // 角色改动很少，5 分钟内不重复请求
        staleTime: 5 * 60 * 1000,
        queryFn: async () => (await sdkListRoles()).data!,
    })
}
