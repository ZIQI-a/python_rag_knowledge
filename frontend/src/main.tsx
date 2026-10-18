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

// 先加载本地存储的用户信息
useAuthStore.getState().hydrate()

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
        <ConfigProvider locale={zhCN} theme={{token: {colorPrimary: '#1677ff'}}}>
            <AntdApp>
                <QueryClientProvider client={queryClient}>
                    <RouterProvider router={router}/>
                </QueryClientProvider>
            </AntdApp>
        </ConfigProvider>
    </StrictMode>,
)
