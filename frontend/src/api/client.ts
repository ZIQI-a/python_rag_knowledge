import { client } from '@/client/client.gen'
import { formatApiError } from "@/utils/errors.ts";
import {message} from "antd";
import {getAuthToken, useAuthStore} from "@/stores/authStore.ts";

// 设置全局配置
client.setConfig({
    baseUrl: '',
    throwOnError: true,
})

// 请求拦截器
client.interceptors.request.use((request) => {
    const token = getAuthToken()
    if (token && !request.headers.has('Authorization')) {
        request.headers.set('Authorization', `Bearer ${token}`)
    }
    return request
})

let redirectingToLogin = false

// 响应拦截器
client.interceptors.response.use(async (response) => {

    if(response.status === 401) {
        useAuthStore.getState().logout()
        if (!redirectingToLogin && window.location.pathname !== '/login') {
            redirectingToLogin = true
            const back = window.location.pathname + window.location.search
            window.location.replace(`/login?back=${encodeURIComponent(back)}`)
        }
        // 在登录页是展示后端返回的错误
        if (window.location.pathname === '/login') {
            message.error(await formatApiError(response))
        }
        return response
    }
    if(!response.ok) {
        message.error(await formatApiError(response))
    }
    return response;
})
