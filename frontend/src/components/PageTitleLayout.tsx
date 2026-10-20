import {useEffect} from 'react'
import {Outlet, useLocation} from 'react-router-dom'
import {getPageTitle} from '@/config/brand'

/** 同时覆盖登录页和鉴权业务页，随路由更新浏览器标签。 */
export function PageTitleLayout() {
    const {pathname} = useLocation()
    useEffect(() => {
        document.title = getPageTitle(pathname)
    }, [pathname])
    return <Outlet/>
}
