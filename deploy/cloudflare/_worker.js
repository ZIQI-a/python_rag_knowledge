/** Pages 同源 API 转发：保留认证、查询参数和 SSE 流，不在边缘缓存私有数据。 */
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/mcp" || url.pathname.startsWith("/mcp/")) {
      return new Response("MCP 公网入口尚未启用", { status: 404 });
    }
    if (url.pathname !== "/api" && !url.pathname.startsWith("/api/")) {
      return env.ASSETS.fetch(request);
    }

    let target;
    try {
      target = new URL(env.API_ORIGIN);
      // 固定 HTTPS 后端来源；拒绝错误地指向前端自身造成递归转发。
      if (target.protocol !== "https:" || target.origin === url.origin ||
          target.username || target.password || target.pathname !== "/" ||
          target.search || target.hash) {
        throw new Error("无效的 API_ORIGIN");
      }
    } catch {
      return new Response("请在 Pages 中配置有效的 HTTPS API_ORIGIN", {
        status: 503, headers: { "Cache-Control": "no-store" },
      });
    }

    target.pathname = url.pathname;
    target.search = url.search;
    try {
      // Request 直接转发上传流；manual 避免将认证头自动携带到重定向目标。
      const upstreamRequest = new Request(target, request);
      // 回源 Host 与后端域名一致，让 OpenResty 选中rag-knowledge站点。
      upstreamRequest.headers.set("Host", target.host);
      const upstream = await fetch(upstreamRequest, {
        redirect: "manual",
        cf: { cacheEverything: false, cacheTtl: 0 },
      });
      // 直接传递响应流，禁止通过 text/json 读取后再返回，否则 SSE 会被缓冲。
      const response = new Response(upstream.body, upstream);
      response.headers.set("Cache-Control", "no-store");
      return response;
    } catch {
      return new Response("后端暂时无法连接，请稍后重试", {
        status: 502, headers: { "Cache-Control": "no-store" },
      });
    }
  },
};
