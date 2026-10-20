import type {ReactNode} from 'react'
import {ConfigProvider} from 'antd'
import zhCN from 'antd/locale/zh_CN'
import {wenjinTheme} from '@/config/theme'
import {useMediaQuery} from '@/utils/useMediaQuery'

/** 将系统减少动画偏好同步给 Ant Design，保留统一中文与主题配置。 */
export function AppThemeProvider({children}: {children: ReactNode}) {
    const reducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)')
    return <ConfigProvider locale={zhCN}
        theme={{...wenjinTheme, token: {...wenjinTheme.token, motion: !reducedMotion}}}>
        {children}
    </ConfigProvider>
}
