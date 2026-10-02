import type React from "react";


/** ReactMarkdown 共享的 GFM 表格 + 行内代码样式组件 */
export const gfmComponents = {
    table: (props: React.ComponentProps<'table'>) => (
        <div style={{ overflowX: 'auto', margin: '8px 0' }}>
            <table
                {...props}
                style={{
                    borderCollapse: 'collapse',
                    width: '100%',
                    fontSize: 13,
                    background: '#fff',
                }}
                />
        </div>
    ),
    th: (props: React.ComponentProps<'th'>) => (
        <th
            {...props}
            style={{
                border: '1px solid #ddd',
                padding: '8px 16px',
                textAlign: 'left',
                fontWeight: 'bold',
                background: '#fafafa',
            }}
        />
    ),
    td: (props: React.ComponentProps<'td'>) => (
        <td
            {...props}
            style={{ border: '1px solid #ddd', padding: '8px 16px', verticalAlign: 'top' }}
            />
    ),
    code: (props: React.ComponentProps<'code'>) => (
        <code
            {...props}
            style={{ background: 'rgba(0,0,0,0.06)', padding: '1px 4px', borderRadius: 3, fontSize: '0.9rem' }}
        />
    )
}
