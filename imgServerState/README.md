# imgServerState 项目分析

## 项目概述

**imgServerState** 是一个基于 FastAPI 的图片处理和 AI 识别服务系统，用于处理和分析借贷相关的单据图片（如微粒贷相关单据）。该项目集成了图片上传、存储、OCR 识别、AI 提取等完整的业务流程。

### 核心功能
- 图片上传与存储
- 图片的 OCR 识别与提取
- AI 模型（通义万象/Qwen）进行信息智能抽取
- 数据库存储与管理
- 企业微信机器人通知
- 负载均衡与 Nginx 配置管理
- 批量数据清理与日志管理

---

## 项目结构

```
imgServerState/
├── 核心模块
│   ├── imgServerFastApi.py       # FastAPI 服务主入口，定义 REST API 接口
│   ├── agentTools.py             # 核心工具类，包含 AI 代理和图片处理逻辑
│   ├── recordPngInfo.py          # 图片信息记录与企业微信通知
│   ├── tools.py                  # 打包脚本，用于生成可执行文件
│   │
├── 辅助模块
│   ├── retrywork.py              # 重试机制，用于处理失败图片的重新分析
│   ├── seeServerIsAlready.py    # 服务器健康检查，检测负载均衡配置
│   ├── updateNginx.py            # Nginx 配置远程更新工具
│   ├── agentTools_Kimi.py        # 旧版本（基于 Kimi AI 的实现）
│   ├── agentToolsOld2.py         # 旧版本备份
│   ├── agentTools_OLD1020_不放大版本.py  # 旧版本备份（无图片放大处理）
│   │
├── 数据处理脚本
│   ├── 日清脚本.py                # 每日数据清理脚本，截断数据库表
│   ├── 脱敏脚本.py                # 数据脱敏脚本，隐藏敏感信息
│   │
├── 配置与文件
│   ├── files/
│   │   └── loadbalance.conf      # Nginx 负载均衡配置文件
│   │
└── 测试目录
    └── test/
        ├── base64Work.py         # Base64 编解码测试
        ├── idNum.py              # 身份号处理测试
        ├── readExcel.py          # Excel 读取测试
        ├── testUUIDWork.py       # UUID 生成测试
        ├── insert3Billow.py      # 数据库插入测试
        └── oneDemo.html          # 前端演示页面
```

---

## 核心模块详解

### 1. **imgServerFastApi.py** - 主服务器
FastAPI 框架搭建的 HTTP 服务，提供以下核心接口：

#### API 接口列表
| 接口 | 方法 | 功能 | 参数 |
|------|------|------|------|
| `/upload` | POST | 上传图片并自动处理 | `file`, `token`, `fromIp` |
| `/retryImage` | POST | 重新处理失败的图片 | `imagePath`, `ip` |
| `/image/{file_name}` | GET | 下载或查看已处理的图片 | `file_name`, `token` |
| `/excel` | POST | 上传 Excel 文件测试 | `file` |

#### 关键特性
- **认证机制**：使用 Token 验证（支持 Query 参数 `?token=` 或 Header 中的 `Bearer` 令牌）
- **跨域支持**：允许所有域名的 CORS 请求（生产环境应收窄）
- **异步处理**：使用 ThreadPoolExecutor 线程池异步处理图片（最多 26 个线程）
- **IP 识别**：从 HTTP Header 的 `X-Real-IP` 获取客户端真实 IP
- **文件管理**：自动创建 `images/` 目录存储上传的图片

---

### 2. **agentTools.py** - 核心业务逻辑
包含两个主要类和多个工具函数：

#### 核心类
**`AgentsTools` 类**：数据库与 AI 集成
- 连接 MySQL 数据库（`ioscar_info` 库的 `img_table` 表）
- 调用阿里云通义万象（Qwen VL Max）进行图片内容智能识别
- 从 OCR 结果中提取关键字段（微粒贷号、卡号、账龄等）

**`ThreadAnayPngWork` 类**：线程化图片处理
- 执行完整的图片处理流程：接收图片 → OCR 识别 → AI 提取 → 数据库存储 → 通知企业微信
- 支持异步处理，避免阻塞主线程

#### 工具类 `PicUtils`
提供图片处理实用方法：
| 方法 | 功能 |
|------|------|
| `crop_left_third_and_enlarge()` | 裁剪图片左侧 1/3 并放大 |
| `enlarge_whole()` | 整张图片等比放大 |
| `crop_1_3_card_img()` | 提取卡号区域并放大 |
| `crop_1_3_eventid_img()` | 提取微粒贷号区域并放大 |
| `corp_1_3_org()` | 提取机构信息区域并放大 |

#### 关键函数
- `stream_request()` - 处理阿里云 API 流式响应
- `get_logger()` - 日志记录器配置（支持文件滚动和控制台输出）

---

### 3. **recordPngInfo.py** - 信息记录与通知
负责记录处理结果和发送企业微信通知。

#### 核心函数
| 函数 | 功能 |
|------|------|
| `send_robot()` | 发送企业微信群机器人消息 |
| `get_zling()` | 从 OCR 结果中提取账龄信息 |
| `get_retry_json()` | 调用 Qwen AI 进行数据抽取，返回结构化 JSON |

#### 数据流程
1. 调用本地 OCR 服务（`http://10.255.101.112:9006/ocr`）识别图片
2. 将 OCR 结果和业务提示词发送给阿里云通义万象 API
3. AI 返回清洗后的 JSON 结构（包含微粒贷号、卡号等）
4. 通过企业微信机器人发送处理结果通知

---

### 4. **retrywork.py** - 失败图片重试
提供重新处理失败或未处理完成的图片的机制。

---

### 5. **seeServerIsAlready.py** - 服务器健康检查
从 `files/loadbalance.conf` 读取 Nginx 负载均衡配置中的服务器列表，逐个检测其健康状态。

```python
# 检查逻辑
读取配置 → 解析服务器地址 → 发送 HTTP GET /ok → 检查响应状态
```

---

### 6. **updateNginx.py** - Nginx 配置更新
使用 Paramiko SSH 库远程更新 Nginx 配置：
1. 连接到远程服务器（`10.255.100.202`）
2. 上传 `files/loadbalance.conf` 到 `/etc/nginx/conf.d/`
3. 验证配置语法（`nginx -t`）
4. 重新加载 Nginx（`nginx -s reload`）

---

### 7. **日清脚本.py** - 每日数据清理
定时清理数据库中的旧数据，避免数据堆积：
- 截断（TRUNCATE）`info_save`、`img_table`、`final_case` 表
- 记录操作日志到 JSON 文件

---

### 8. **脱敏脚本.py** - 数据脱敏
（文件内容未完整读取，但推测用于隐藏敏感数据如身份证号、卡号等）

---

## 数据库设计

### 连接信息
- **主库**：`10.255.100.202:3306`（生产库，用户：`root` / 密码：`123.com`）
- **模型库**：`10.255.101.169:3306`（存储 AI 模型 API Key，用户：`root` / 密码：`cbf123456.`）
- **库名**：`ioscar_info`

### 主要表结构
| 表名 | 用途 |
|------|------|
| `img_table` | 存储上传的图片和识别结果 |
| `info_save` | 存储处理后的结构化数据 |
| `final_case` | 存储最终的案件数据 |
| `key_info` | 存储阿里云 Qwen API Key |

### 关键查询
```sql
-- 查询未审核的微粒贷单据
SELECT * FROM img_table 
WHERE check_ok IS NULL 
  AND card_id LIKE '%DS%' 
  AND insert_date > '2025-12-16 04:08:00'
```

---

## 依赖与环境

### Python 依赖
- **FastAPI** - Web 框架
- **Uvicorn** - ASGI 服务器
- **Pillow (PIL)** - 图片处理
- **PyMySQL** - MySQL 数据库驱动
- **Requests** - HTTP 客户端库
- **Paramiko** - SSH 远程连接
- **阿里云 SDK** - 调用 Qwen VL Max 模型

### 外部服务
| 服务 | 地址 | 用途 |
|------|------|------|
| 本地 OCR | `http://10.255.101.112:9006/ocr` | 图片文字识别 |
| 阿里云 Qwen | `https://dashscope.aliyuncs.com/...` | AI 信息提取 |
| 企业微信机器人 | `https://qyapi.weixin.qq.com/...` | 消息通知 |

---

## 业务流程

### 完整的图片处理流程
```
1. 用户上传图片
   ↓
2. 服务器保存图片到 images/ 目录
   ↓
3. 启动异步线程处理
   ↓
4. ThreadAnayPngWork.work() 执行：
   a) 调用本地 OCR 识别（获取原始文本）
   b) 通过 Qwen AI 进行信息提取（结构化数据）
   c) 数据库存储处理结果
   d) 企业微信通知处理完成
   ↓
5. 返回可访问的图片 URL
   ↓
6. 如果处理失败，可通过 /retryImage 接口重新处理
```

---

## 部署与配置

### 启动服务
```bash
# 方式 1：直接运行
python imgServerFastApi.py

# 方式 2：使用 Uvicorn
uvicorn imgServerFastApi:app --host 0.0.0.0 --port 8000

# 方式 3：打包成可执行文件（Windows）
python tools.py  # 使用 PyInstaller 打包
```

### 配置文件说明
- **`files/loadbalance.conf`**：Nginx 负载均衡配置，定义了后端服务器列表
- **`API_TOKEN`**：当前设置为 `cbf123456.`，生产环境应使用 JWT 或 Redis

### 日志目录
- 日志文件自动生成在 `logs/` 目录
- 每天午夜自动切割日志（保留最近 2 份）

---

## 安全考虑

### 当前问题
⚠️ **生产环保问题**：
1. **Token 硬编码**：API Token 直接在代码中，应使用环境变量或配置文件
2. **数据库密码硬编码**：多处代码包含明文数据库密码
3. **CORS 开放**：允许所有域名访问，应在生产环境收窄
4. **敏感数据日志**：日志中可能包含用户敏感信息

### 建议改进
- 使用 `.env` 文件或环境变量管理敏感配置
- 实现 JWT 或 OAuth2 认证机制
- 限制 CORS 到特定域名
- 添加数据脱敏日志中间件
- 使用数据库连接池
- 添加请求速率限制（Rate Limiting）

---

## 文件版本管理

项目中存在多个版本的 `agentTools`：
- **`agentTools.py`**：当前生产版本（推荐使用）
- **`agentTools_Kimi.py`**：基于 Kimi AI 的旧实现
- **`agentTools_OLD1020_不放大版本.py`**：无图片放大功能的版本
- **`agentToolsOld2.py`**：其他旧版本备份

**建议**：清理无用的旧版本文件以减少维护复杂度。

---

## 测试模块

`test/` 目录包含各种单元测试和功能演示：
- **base64Work.py**：Base64 编码/解码测试
- **idNum.py**：身份号处理和验证
- **readExcel.py**：Excel 文件读取
- **testUUIDWork.py**：UUID 生成和管理
- **insert3Billow.py**：数据库插入操作
- **oneDemo.html**：前端演示界面

---

## 总结

**imgServerState** 是一个功能完整的图片处理和 AI 识别服务系统，适用于借贷行业的单据自动化处理。其主要特点是：

✅ **优势**：
- 完整的端到端处理流程
- 集成多个 AI 服务（OCR + Qwen）
- 支持异步处理和重试机制
- 包含数据库管理和日志系统
- 支持 Nginx 负载均衡配置管理

⚠️ **改进空间**：
- 需要改进安全配置（移除硬编码密码和 Token）
- 代码版本管理需整理
- 应添加更完整的错误处理和日志记录
- 建议编写单元测试
- 性能优化（如数据库连接池、缓存）

---

**最后更新**：2026 年 5 月 20 日
**分析者**：GitHub Copilot
