/** 顶栏用户菜单 */
import { App as AntdApp, Avatar, Dropdown, Space, Tag, Typography } from 'antd'
import {useNavigate} from "react-router-dom";
import {useQueryClient} from "@tanstack/react-query";
import {useAuthStore} from "@/stores/authStore.ts";
import {LogoutOutlined, UserOutlined} from "@ant-design/icons";

export function UserMenu() {
    const { message } = AntdApp.useApp()
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
            menu={{
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
            <Space style={{ cursor: 'pointer' }}>
                <Avatar size="small" icon={<UserOutlined />} />
                <Typography.Text>{user.displayName}</Typography.Text>
                {user.isAdmin ? <Tag color="gold">管理员</Tag> : null}
            </Space>
        </Dropdown>
    )

}

