/** 路由守卫 */
import {Navigate, Outlet, useLocation} from "react-router-dom";
import {useAuthStore} from "@/stores/authStore.ts";
import {useQuery} from "@tanstack/react-query";
import {currentUserKey} from "@/api/queryKeys.ts";
import {fetchCurrentUser} from "@/api/auth.ts";
import {useEffect} from "react";
import {PageLoading} from '@/components/PageState';


export function RequireAuth() {
    const location =useLocation()
    const ready = useAuthStore((s) => s.ready)
    const token = useAuthStore((s) => s.token)
    const setUser = useAuthStore((s) => s.setUser)

    const { data: freshUser } = useQuery({
        queryKey: currentUserKey,
        queryFn: fetchCurrentUser,
        enabled: ready && Boolean(token),
        staleTime: 60_000,
        retry: false
    })

    useEffect(() => {
        if(freshUser) {
            setUser(freshUser)
        }
    }, [freshUser, setUser]);

    if(!ready) {
        return (
            <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center' }}>
                <PageLoading/>
            </div>
        )
    }
    if(!token) {
        const back = encodeURIComponent(location.pathname + location.search)
        return <Navigate to={`/login?back=${back}`} replace />
    }
    return <Outlet />
}
