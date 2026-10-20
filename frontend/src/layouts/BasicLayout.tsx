import {Layout, Menu, type MenuProps} from "antd";
import {
    DashboardOutlined,
    ExperimentOutlined,
    FileTextOutlined,
    MessageOutlined, SafetyOutlined,
    TeamOutlined
} from "@ant-design/icons";
import {Link, Outlet, useLocation} from 'react-router-dom';
import {useAuthStore} from "@/stores/authStore.ts";
import {UserMenu} from "@/components/UserMenu.tsx";
import {useState} from 'react';
import {BrandLogo} from '@/components/BrandLogo';
import {BRAND} from '@/config/brand';
import {PALETTE} from '@/config/theme';


const {Header, Sider, Content} = Layout;

const baseMenuItems: NonNullable<MenuProps["items"]> = [
    {
        key: '/',
        icon: <DashboardOutlined />,
        label: <Link to={'/'}>问津亭</Link>
    },
    {
        key: '/documents',
        icon: <FileTextOutlined />,
        label: <Link to={'/documents'}>藏书阁</Link>,
    },
    {
        key: '/chat',
        icon: <MessageOutlined />,
        label: <Link to={'/chat'}>万事知</Link>,
    },
]

const adminMenuItems: NonNullable<MenuProps["items"]> = [
    {
        key: '/evaluation',
        icon: <ExperimentOutlined />,
        label: <Link to={'/evaluation'}>试津</Link>,
    },
    {
        key: '/users',
        icon: <TeamOutlined />,
        label: <Link to={'/users'}>名籍</Link>,
    },
    {
        key: '/roles',
        icon: <SafetyOutlined />,
        label: <Link to={'/roles'}>司津</Link>,
    },
]



// 使选中的菜单保持高亮
function resolveSelectedKey(pathname: string): string {
    if(pathname.startsWith('/documents')) return '/documents';
    if(pathname.startsWith('/chat')) return '/chat';
    if(pathname.startsWith('/evaluation')) return '/evaluation';
    if(pathname.startsWith('/users')) return '/users';
    if(pathname.startsWith('/roles')) return  '/roles';
    return '/'
}

export function BasicLayout() {
    const [collapsed, setCollapsed] = useState(false)
    const location = useLocation()
    const selectedKey = resolveSelectedKey(location.pathname)
    const isAdmin = useAuthStore((s) => Boolean(s.user?.isAdmin))
    const menuItems = isAdmin
        ? [...baseMenuItems, ...adminMenuItems] : baseMenuItems

    return (
        <Layout style={{minHeight: '100vh'}}>
            <Sider theme="light" breakpoint={'lg'} collapsedWidth={64} collapsed={collapsed} onCollapse={setCollapsed}
                style={{borderRight: `1px solid ${PALETTE.line}`}}>
                <Link to="/" aria-label={`${BRAND.name}首页`}
                    style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        padding: '20px 8px',
                    }}
                >
                    <BrandLogo size={32} showText={!collapsed}/>
                </Link>
                <Menu
                    mode={'inline'}
                    theme={'light'}
                    selectedKeys={[selectedKey]}
                    items={menuItems}
                />
            </Sider>
            <Layout>
                <Header style={{
                    borderBottom: `1px solid ${PALETTE.line}`, paddingLeft: 24, paddingRight: 24,
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    fontSize: 16
                }}>
                    {BRAND.productName}
                    <UserMenu />
                </Header>

                <Content style={{margin: 24}}>
                    <Outlet />
                </Content>
            </Layout>
        </Layout>
    )
}
