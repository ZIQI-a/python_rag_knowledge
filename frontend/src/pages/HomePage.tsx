import { Card, Col, Row, Typography } from 'antd'

const { Title, Paragraph } = Typography

export function HomePage() {
  return (
    <>
      <Title level={3}>欢迎使用问津 RAG 知识库</Title>
      <Paragraph type="secondary">
        企业文档统一采集、切分、向量化，提供基于私有知识的智能问答与检索。
      </Paragraph>
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} md={8}>
          <Card title="文档管理">企业文档采集与切分（建设中）</Card>
        </Col>
        <Col xs={24} md={8}>
          <Card title="知识问答">基于私有知识的 RAG 问答（建设中）</Card>
        </Col>
        <Col xs={24} md={8}>
          <Card title="服务状态">后端健康检查 API 已就绪</Card>
        </Col>
      </Row>
    </>
  )
}
