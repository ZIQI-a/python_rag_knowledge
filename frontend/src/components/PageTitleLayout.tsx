import {useEffect} from 'react'
import {Outlet, useLocation, useNavigation} from 'react-router-dom'
import {getPageMetadata} from '@/config/brand'
import {PageLoading} from '@/components/PageState'

/** 同时覆盖登录页和鉴权业务页，随路由同步标签与分享摘要。 */
export function PageTitleLayout() {
    const {pathname} = useLocation()
    const navigation = useNavigation()
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
    return navigation.state === 'loading' ? <PageLoading/> : <Outlet/>
}
