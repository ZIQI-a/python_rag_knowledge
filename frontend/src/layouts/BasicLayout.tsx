import {Layout, Menu} from "antd";
import {DashboardOutlined, FileTextOutlined, MessageOutlined} from "@ant-design/icons";
import {Link, Outlet, useLocation} from 'react-router-dom';


const {Header, Sider, Content} = Layout;

const menuItems = [
    {
        key: '/',
        icon: <DashboardOutlined />,
        label: <Link to={'/'}>首页</Link>
    },
    {
        key: '/documents',
        icon: <FileTextOutlined />,
        label: <Link to={'/documents'}>文档管理</Link>,
    },
    {
        key: '/chat',
        icon: <MessageOutlined />,
        label: '知识问答',
        disabled: true
    },
]

// 使选中的菜单保持高亮
function resolveSelectedKey(pathname: string): string {
    if(pathname.startsWith('/documents')) return '/documents';
    if(pathname.startsWith('/chat')) return '/chat';
    return '/'
}

export function BasicLayout() {
    const location = useLocation();
    const selectedKey = resolveSelectedKey(location.pathname)

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
                <Header style={{ color: "#fff", paddingLeft: 24, fontSize:16 }}>
                    问津-知识库
                </Header>
                <Content style={{margin: 24}}>
                    <Outlet />
                </Content>
            </Layout>
        </Layout>
    )
}
