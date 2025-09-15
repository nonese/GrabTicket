# GrabTicket

一个简单的抢票示例项目，包含 FastAPI 编写的后端和基于 Vue 3 + Vite 的前端。后端使用 SQLite 保存数据，实现了用户注册/登录、活动查询与抢票等接口。

## 目录结构

- `backend/`：FastAPI 后端源码
- `frontend/`：Vue 前端源码

## 环境准备

### 后端

- Python 3.11+
- `pip`

安装依赖：

```bash
pip install fastapi uvicorn sqlalchemy passlib[bcrypt] python-jose
```

### 前端

- Node.js 18+
- `npm`

## 本地运行

### 启动后端

```bash
uvicorn backend.main:app --reload
```

服务器默认监听在 <http://localhost:8000>，首次运行会在项目根目录生成 `app.db` 数据库文件。

### 启动前端

开发阶段可以使用 Vite 的开发服务器，需配置代理以转发 API 请求到后端，在 `frontend/vite.config.js` 中添加：

```js
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/auth': 'http://localhost:8000',
      '/events': 'http://localhost:8000',
      '/ws': { target: 'ws://localhost:8000', ws: true }
    }
  }
})
```

然后执行：

```bash
cd frontend
npm install
npm run dev
```

浏览器访问 <http://localhost:5173> 即可看到界面。若需构建静态文件，可运行 `npm run build`，输出位于 `frontend/dist`。

## 使用流程

1. **注册用户**

   ```bash
   curl -X POST http://localhost:8000/auth/register \
        -H "Content-Type: application/json" \
        -d '{"username":"alice","password":"secret"}'
   ```

2. **登录获取令牌**

   ```bash
   curl -X POST http://localhost:8000/auth/login \
        -d "username=alice&password=secret"
   ```

   响应中 `access_token` 字段即为后续请求所需的 Bearer Token。

3. **创建活动**（需携带登录令牌）

   ```bash
   curl -X POST http://localhost:8000/events \
        -H "Authorization: Bearer <token>" \
        -H "Content-Type: application/json" \
       -d '{"title":"音乐会","sale_start_time":"2024-04-01T10:00:00","start_time":"2024-05-01T19:00:00"}'
   ```

4. **抢票**

   前端通过 WebSocket 与后端交互抢票：

   - 连接地址：`ws://localhost:8000/ws/events/{event_id}?token=<登录令牌>`
   - 后端会持续通过该连接广播各票种剩余数量。
   - 发送 `{"action":"grab","ticket_type_id":1}` 抢购指定票种，
     服务端按顺序队列依次处理请求；
     库存不足时会返回失败并附带其他仍有余票的票种信息。

## 备注

- 数据库存储在 `app.db`，删除该文件可以重置数据。
- 当前项目未包含活动与票种的管理界面，可直接操作数据库或扩展接口以初始化数据。

