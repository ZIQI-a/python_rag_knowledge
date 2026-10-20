import {Button, Drawer, Layout, Menu, type MenuProps} from "antd";
import {
    MenuOutlined,
    DashboardOutlined,
    ExperimentOutlined,
    FileTextOutlined,
    MessageOutlined, SafetyOutlined,
    TeamOutlined
} from "@ant-design/icons";
import {Link, Outlet, useLocation} from 'react-router-dom';
import {useAuthStore} from "@/stores/authStore.ts";
import {UserMenu} from "@/components/UserMenu.tsx";
import {useEffect, useRef, useState} from 'react';
import {useMediaQuery} from '@/utils/useMediaQuery';
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
    const isMobile = useMediaQuery('(max-width: 767px)')
    const [menuOpen, setMenuOpen] = useState(false)
    const [collapsed, setCollapsed] = useState(false)
    const mainRef = useRef<HTMLElement>(null)
    const location = useLocation()
    const selectedKey = resolveSelectedKey(location.pathname)
    const isAdmin = useAuthStore((s) => Boolean(s.user?.isAdmin))
    const menuItems = isAdmin
        ? [...baseMenuItems, ...adminMenuItems] : baseMenuItems

    // 路由切换后焦点进入内容区，便于键盘和读屏继续操作；容器自身不画焦点框，内部控件保留焦点样式。
    useEffect(() => {
        if (mainRef.current) mainRef.current.scrollTop = 0
        mainRef.current?.focus({preventScroll: true})
    }, [location.pathname])

    // 侧栏和抽屉复用菜单，保持文案、选中态与权限一致。
    const navigation = (compact: boolean) => <>
        <Link to="/" aria-label={`${BRAND.name}首页`} onClick={() => setMenuOpen(false)}
            style={{display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px 8px'}}>
            <BrandLogo size={32} showText={!compact}/>
        </Link>
        <Menu mode="inline" theme="light" selectedKeys={[selectedKey]} items={menuItems}
            onClick={() => setMenuOpen(false)}/>
    </>

    return (
        <Layout style={{height: '100dvh', overflow: 'hidden'}}>
            {!isMobile && <Sider theme="light" width={200} breakpoint="lg" collapsedWidth={64}
                collapsed={collapsed} onCollapse={setCollapsed} style={{borderRight: `1px solid ${PALETTE.line}`, overflowY: 'auto'}}>
                {navigation(collapsed)}
            </Sider>}
            <Drawer title="主菜单" placement="left" open={isMobile && menuOpen} onClose={() => setMenuOpen(false)}
                size={280} styles={{body: {padding: 0}}}>
                {navigation(false)}
            </Drawer>
            <Layout style={{minWidth: 0}}>
                <Header style={{borderBottom: `1px solid ${PALETTE.line}`, paddingInline: isMobile ? 12 : 24,
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, flexShrink: 0}}>
                    <div style={{display: 'flex', alignItems: 'center', gap: 8, minWidth: 0}}>
                        {isMobile && <Button type="text" icon={<MenuOutlined/>} aria-label="打开主菜单"
                            aria-expanded={menuOpen} onClick={() => setMenuOpen(true)}/>}
                        <span style={{whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>
                            {isMobile ? BRAND.name : BRAND.productName}
                        </span>
                    </div>
                    <UserMenu/>
                </Header>
                <Content ref={mainRef} role="main" tabIndex={-1}
                    style={{padding: isMobile ? 12 : 24, minWidth: 0, minHeight: 0, overflowY: 'auto', overflowX: 'hidden', outline: 'none'}}>
                    <Outlet/>
                </Content>
            </Layout>
        </Layout>
    )
}
