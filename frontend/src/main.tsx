import '@/api/client.ts'
import {StrictMode} from 'react'
import {createRoot} from 'react-dom/client'
import {RouterProvider} from 'react-router-dom'
import {QueryClient, QueryClientProvider} from "@tanstack/react-query";
import {App as AntdApp, ConfigProvider} from 'antd'
import zhCN from 'antd/locale/zh_CN'
import './index.css'
import {router} from './routes'
import {useAuthStore} from "@/stores/authStore.ts";
import {PALETTE, wenjinTheme} from '@/config/theme'

// 先加载本地存储的用户信息
useAuthStore.getState().hydrate()

// 为请求拦截器等处的静态提示提供同一套主题与语言配置。
ConfigProvider.config({
    holderRender: (children) => (
        <ConfigProvider locale={zhCN} theme={wenjinTheme}>{children}</ConfigProvider>
    ),
})

// 构建查询服务
const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            retry: 1,
            staleTime: 30_000,
            refetchOnWindowFocus: false,
        }
    }
})

const root = document.getElementById('root')
if (!root) throw new Error('根元素找不到')

createRoot(root).render(
    <StrictMode>
        <ConfigProvider locale={zhCN} theme={wenjinTheme}>
            <AntdApp style={{minHeight: '100vh', background: PALETTE.paper, color: PALETTE.ink}}>
                <QueryClientProvider client={queryClient}>
                    <RouterProvider router={router}/>
                </QueryClientProvider>
            </AntdApp>
        </ConfigProvider>
    </StrictMode>,
)
