/** 管理员页面拦截页 */
import {useAuthStore} from "@/stores/authStore.ts";
import {Result} from "antd";
import {Outlet} from "react-router-dom";

export function RequireAdmin() {
    const user = useAuthStore((s) => s.user)
    if(!user?.isAdmin) {
        return (
            <Result
                status="403"
                title="403"
                subTitle="页面仅管理员可访问"
            />
        )
    }
    return <Outlet />
}
