# GrabTicket

一个简单的抢票示例项目，包含 FastAPI 编写的后端和基于 Vue 3 + Vite 的前端。后端使用 SQLite 保存数据，实现了用户注册/登录、活动查询与抢票等接口。

## 目录结构

- `backend/`：FastAPI 后端源码
- `frontend/`：Vue 前端源码
- `static/`：默认静态资源目录（可放置前端构建产物）

## 环境准备

### 后端

- Python 3.11+
- `pip`

安装依赖：

```bash
pip install -r backend/requirements.txt
```

常用环境变量：

- `DATABASE_URL`：数据库连接字符串，默认 `sqlite:///./app.db`
- `BACKEND_CORS_ORIGINS`：允许访问的前端地址，使用逗号分隔，例如 `https://foo.com,https://bar.com`

### 前端

- Node.js 18+
- `npm`

## 本地运行

### 启动后端

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

服务监听在 <http://localhost:8000>。首次运行会在项目根目录生成 `app.db` 数据库文件；若通过 `DATABASE_URL` 指定为其他路径，请确保目标目录具有写入权限。

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
      '/orders': 'http://localhost:8000',
      '/admin': 'http://localhost:8000',
      '/users': 'http://localhost:8000',
      '/static': 'http://localhost:8000',
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

浏览器访问 <http://localhost:5173> 即可看到界面。

可在 `frontend/.env` 中定制部署参数：

- `VITE_WS_HOST`：WebSocket 地址（默认回退到浏览器地址）
- `VITE_API_BASE`：HTTP API 地址，留空则使用当前网页域名

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

## 生产部署与打包

1. 构建前端静态资源：

   ```bash
   cd frontend
   npm ci
   npm run build
   ```

   构建前可通过 `.env` 文件设置 `VITE_WS_HOST` 与 `VITE_API_BASE` 指向实际后端地址。

2. 将 `frontend/dist/` 内容复制到项目根目录的 `static/` 文件夹，或上传到独立的静态文件服务器。

3. 启动后端服务，监听公网地址：

   ```bash
   uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```

   如需允许跨域请求，可设置 `BACKEND_CORS_ORIGINS` 列表。

## Docker 部署

项目提供多阶段构建的 `Dockerfile`，能一次性打包前端和后端：

```bash
docker build -t grabticket .
docker run -d --name grabticket -p 8000:8000 \
  -e BACKEND_CORS_ORIGINS="https://your-frontend-domain.com" \
  -e DATABASE_URL=sqlite:////data/app.db \
  -v $(pwd)/data:/data grabticket
```

也可以使用 `docker-compose`：

```bash
docker compose up -d
```

默认会将数据库持久化到宿主机的 `./data/app.db`，可根据需求调整 `docker-compose.yml` 中的配置。

## 备注

- 数据库存储在 `DATABASE_URL` 指定的位置，默认是项目根目录下的 `app.db`。删除该文件可以重置数据。
- 当前项目未包含活动与票种的管理界面，可直接操作数据库或扩展接口以初始化数据。
- 生产环境建议使用 HTTPS 并妥善配置 `SECRET_KEY` 与其他安全相关参数。
