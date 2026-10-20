import type {ReactNode} from 'react'
import {Button, Empty, Result, Space, Spin} from 'antd'
import {Link} from 'react-router-dom'

/** 页面和鉴权加载时提供可被辅助技术识别的反馈。 */
export function PageLoading() {
    return <div role="status" aria-live="polite" style={{padding: 48, textAlign: 'center'}}>
        <Space><Spin/>正在加载，请稍候…</Space>
    </div>
}

/** 列表区分请求失败和空数据，避免将网络错误误报为暂无记录。 */
export function DataState({failed, description = '暂无记录', action, onRetry}: {
    failed?: boolean
    description?: string
    action?: ReactNode
    onRetry?: () => void
}) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE}
        description={failed ? '加载失败，请重试' : description}>
        {failed ? <Button onClick={onRetry}>重新加载</Button> : action}
    </Empty>
}

/** 详情请求失败时保留明确的重试入口，不展示内部异常内容。 */
export function PageFailure({onRetry}: {onRetry: () => void}) {
    return <Result status="error" title="暂时无法加载页面" subTitle="请检查网络连接后重试。"
        extra={<Button type="primary" onClick={onRetry}>重新加载</Button>}/>
}

/** 未匹配的业务地址保留回到首页的入口。 */
export function NotFoundPage() {
    return <Result status="404" title="页面未找到" subTitle="地址可能有误，或页面已移除。"
        extra={<Link to="/"><Button type="primary">返回首页</Button></Link>}/>
}

/** 捕获页面渲染异常，提供整页重新加载，避免继续使用损坏的界面状态。 */
export function RouteErrorPage() {
    return <Result status="error" title="页面暂时出了点问题" subTitle="可以重新加载，或返回首页继续使用。"
        extra={<Space wrap>
            <Button type="primary" onClick={() => window.location.reload()}>重新加载</Button>
            <Link to="/"><Button>返回首页</Button></Link>
        </Space>}/>
}
