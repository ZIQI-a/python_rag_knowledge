import {useEffect} from 'react'
import {Outlet, useLocation} from 'react-router-dom'
import {getPageMetadata} from '@/config/brand'

/** 同时覆盖登录页和鉴权业务页，随路由同步标签与分享摘要。 */
export function PageTitleLayout() {
    const {pathname} = useLocation()
    useEffect(() => {
        const {title, description} = getPageMetadata(pathname)
        document.title = title
        // 更新 index.html 中已有的元信息，切换页面时覆盖旧值。
        const metadata = [
            ['name="description"', description],
            ['property="og:title"', title],
            ['property="og:description"', description],
            ['name="twitter:title"', title],
            ['name="twitter:description"', description],
        ]
        metadata.forEach(([selector, content]) => {
            document.querySelector<HTMLMetaElement>(`meta[${selector}]`)?.setAttribute('content', content)
        })
    }, [pathname])
    return <Outlet/>
}
