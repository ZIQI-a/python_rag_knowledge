/** 登录页面 */
import { App as AntdApp, Button, Card, Form, Input, Typography } from 'antd'
import {useNavigate, useSearchParams} from "react-router-dom";
import {useAuthStore} from "@/stores/authStore.ts";
import {useState} from "react";
import {login} from "@/api/auth.ts";
import {LockOutlined, UserOutlined} from "@ant-design/icons";
import {BrandLogo} from '@/components/BrandLogo';
import {BRAND} from '@/config/brand';

interface LoginFormValues {
    username: string
    password: string
}

export function LoginPage() {
    const { message } = AntdApp.useApp()
    const navigate = useNavigate()
    const [searchParams] = useSearchParams()
    const setAuth = useAuthStore((s) => s.setAuth)
    // 表单提交状态
    const [submitting, setSubmitting] = useState(false)

    // 表单提交处理
    async function onFinish(values: LoginFormValues) {
        setSubmitting(true)
        try {
            const result = await login(values.username, values.password)
            setAuth(result.token, result.user)
            message.success(`欢迎回来，${result.user.displayName}`)
            navigate(searchParams.get('back') || '/', { replace: true })
        } catch {
            // 错误提示已由 client.ts 响应拦截器统一处理，这里只需吞掉异常
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <div
            style={{
                minHeight: '100vh',
                display: 'grid',
                placeItems: 'center',
                background: 'linear-gradient(135deg, #f5f7fb 0%, #e6efff 100%)',
                padding: 24
            }}
        >
            <Card style={{ width: '100%', maxWidth: 360 }} variant="borderless">
                <div style={{display: 'flex', justifyContent: 'center', marginBottom: 16}}>
                    <BrandLogo size={64} showText={false}/>
                </div>
                <Typography.Title level={1} style={{ fontSize: 24, textAlign: 'center', marginBottom: 8 }}>
                    {BRAND.productName}
                </Typography.Title>
                <Typography.Paragraph type="secondary" style={{fontSize: 13, textAlign: 'center', marginBottom: 24}}>
                    {BRAND.description}
                </Typography.Paragraph>
                <Form<LoginFormValues>
                    layout="vertical"
                    onFinish={onFinish}
                    initialValues={{ username: '', password: '' }}
                    autoComplete="off"
                >
                    <Form.Item name="username" label="用户名"
                        rules={[{ required: true, message: '请输入你的用户名' }]}>
                        <Input prefix={<UserOutlined />} placeholder="用户名" autoFocus/>
                    </Form.Item>
                    <Form.Item name="password" label="密码"
                       rules={[{ required: true, message: '请输入密码' }]}>
                        <Input.Password prefix={<LockOutlined />} placeholder="密码" />
                    </Form.Item>
                    <Form.Item style={{ marginBottom: 8 }}>
                        <Button type="primary" htmlType="submit" block loading={submitting}>
                            登入渡口
                        </Button>
                    </Form.Item>
                </Form>
                <Typography.Paragraph
                    type="secondary"
                    style={{ marginTop: 8, marginBottom: 0, fontSize: 12, textAlign: 'center' }}
                >
                    默认账号密码都是admin, 登录后及时修改
                </Typography.Paragraph>
            </Card>
        </div>
    )
}
