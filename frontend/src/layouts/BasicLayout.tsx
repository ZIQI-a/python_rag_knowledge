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
    const location = useLocation()
    const selectedKey = resolveSelectedKey(location.pathname)
    const isAdmin = useAuthStore((s) => Boolean(s.user?.isAdmin))
    const menuItems = isAdmin
        ? [...baseMenuItems, ...adminMenuItems] : baseMenuItems

    return (
        <Layout style={{minHeight: '100vh'}}>
            <Sider breakpoint={'lg'} collapsedWidth={64}>
                <div
                    style={{
                        color: '#fff',
                        fontWeight: 600,
                        textAlign: "center",
                        padding: '16px 0',
                        fontSize: 16
                    }}
                >
                    问津RAG知识库
                </div>
                <Menu
                    mode={'inline'}
                    theme={'dark'}
                    selectedKeys={[selectedKey]}
                    items={menuItems}
                />
            </Sider>
            <Layout>
                <Header style={{
                    background: '#fff', paddingLeft: 24, paddingRight: 24,
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    fontSize: 16
                }}>
                    问津-知识库
                    <UserMenu />
                </Header>

                <Content style={{margin: 24}}>
                    <Outlet />
                </Content>
            </Layout>
        </Layout>
    )
}
