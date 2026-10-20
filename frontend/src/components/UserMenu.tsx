/** 顶栏用户菜单 */
import { App as AntdApp, Avatar, Dropdown, Button, Tag, Typography } from 'antd'
import {useNavigate} from "react-router-dom";
import {useQueryClient} from "@tanstack/react-query";
import {useAuthStore} from "@/stores/authStore.ts";
import {LogoutOutlined, UserOutlined} from "@ant-design/icons";
import {useRef, type ComponentRef} from 'react';

export function UserMenu() {
    const { message } = AntdApp.useApp()
    const triggerRef = useRef<ComponentRef<typeof Button>>(null)
    const navigate = useNavigate()
    // 查询客户端
    const queryClient = useQueryClient()
    const user = useAuthStore((s) => s.user)
    const logout = useAuthStore((s) => s.logout)

    if(!user) return null

    // 处理登出
    const handleLogout = () => {
        logout()
        queryClient.clear()
        message.success('已成功退出')
        navigate('/login', { replace: true })
    }

    return (
        <Dropdown
            trigger={['click']}
            autoFocus
            menu={{
                // 等弹层关闭后恢复焦点，避免键盘操作落回页面根节点。
                onKeyDown: (event) => {
                    if (event.key === 'Escape') requestAnimationFrame(() => triggerRef.current?.focus())
                },
                items: [
                    {
                        key: 'logout',
                        icon: <LogoutOutlined />,
                        label: '退出登录',
                        onClick: handleLogout,
                    },
                ],
            }}
            placement="bottomRight"
        >
            <Button ref={triggerRef} type="text" aria-label="用户菜单" style={{height: 'auto', padding: '4px 8px'}}>
                <Avatar size="small" icon={<UserOutlined />} />
                <Typography.Text ellipsis={{tooltip: user.displayName}} style={{maxWidth: 128}}>{user.displayName}</Typography.Text>
                {user.isAdmin ? <Tag color="gold">管理员</Tag> : null}
            </Button>
        </Dropdown>
    )

}

