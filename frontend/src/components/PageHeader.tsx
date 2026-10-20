import type {ReactNode} from 'react'
import {Typography} from 'antd'

/** 统一业务页标题、说明及操作区；窄屏时操作自然换行。 */
export function PageHeader({title, description, actions}: {
    title: string
    description?: ReactNode
    actions?: ReactNode
}) {
    return (
        <header style={{display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 16, marginBottom: 24}}>
            <div style={{flex: '1 1 240px', minWidth: 0}}>
                <Typography.Title level={1} style={{fontSize: 24, margin: 0, overflowWrap: 'anywhere'}}>
                    {title}
                </Typography.Title>
                {description && <Typography.Paragraph type="secondary" style={{margin: '8px 0 0'}}>
                    {description}
                </Typography.Paragraph>}
            </div>
            {actions && <div style={{display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8}}>{actions}</div>}
        </header>
    )
}
