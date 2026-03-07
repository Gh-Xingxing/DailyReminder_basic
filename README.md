# 每日提醒助手（基础版）

基于 GitHub Actions 的每日提醒系统，每天晚上自动推送明日课程、天气、提醒到微信。

## 功能特点

- 📚 **课程提醒**：自动获取明日课程，支持单双周筛选
- 🌤️ **天气预报**：获取明日天气、温度、降雨情况
- ⏰ **每日提醒**：自定义每日提醒内容
- 📱 **微信推送**：通过 Server酱 推送到微信/sever酱APP
---

## 快速开始

### 第一步：Fork 项目到自己的 GitHub

1. 登录你的 GitHub 账号（没有的话先去 [github.com](https://github.com) 注册一个）
2. 打开本项目页面
3. 点击右上角的 **Fork** 按钮
4. 在弹出的页面中点击 **Create fork**，项目就会复制到你的账号下

### 第二步：设置 API 密钥（GitHub Secrets）

这些密钥是项目运行必需的，设置后只有你能看到，别人无法获取。

1. 进入你 Fork 的项目页面
2. 点击上方的 **Settings**（设置）
3. 在左侧菜单找到 **Secrets and variables** → **Actions**
4. 点击 **New repository secret** 按钮，依次添加以下 3 个密钥：

| 密钥名称 | 说明 | 获取方式 |
|---------|------|---------|
| `QWEATHER_KEY` | 和风天气 API 密钥 | 访问 [和风天气开发平台](https://dev.qweather.com/)，注册后在控制台创建应用获取 |
| `QWEATHER_HOST` | 和风天气 API 地址 | 在和风天气控制台的「API 域名」处获取，格式类似 `xxxxxxxx.re.qweatherapi.com` |
| `SERVERCHAN_KEY` | Server酱 SendKey | 访问 [Server酱](https://sc3.ft07.com/)，微信扫码登录后获取 |

> **关于 Server酱**：Server酱提供两种推送方式——微信公众号推送和 App 推送。实际体验下来，App 推送效果更好（公众号推送容易被其他消息刷掉）。本指南提供的网址是 App 版本对应的官网，可根据官网指南下载对应的移动端APP

### 第三步：下载项目到本地

1. 在你的项目页面，点击绿色的 **Code** 按钮
2. 选择 **Download ZIP**
3. 解压下载的 ZIP 文件到任意文件夹

### 第四步：创建本地环境配置文件

1. 进入解压后的文件夹，找到 `.env.example` 文件
2. 复制这个文件，重命名为 `.env`（去掉 .example 后缀）
3. 用记事本打开 `.env` 文件，填入你的 API 密钥：

```
QWEATHER_HOST=你的和风天气API地址
QWEATHER_KEY=你的和风天气API密钥
SERVERCHAN_KEY=你的Server酱SendKey
```

### 第五步：安装 Python 和依赖

**如果你已经安装了 Python，跳过安装步骤。**

1. 访问 [python.org](https://www.python.org/downloads/) 下载 Python
2. 安装时**务必勾选** "Add Python to PATH" 选项
3. 安装完成后，打开命令提示符（按 Win+R，输入 cmd，回车）
4. 输入以下命令安装依赖：

```
pip install -r requirements.txt
```

> 这条命令会自动安装项目所需的 Python 库（Flask、requests 等）

### 第六步：运行配置网页

1. 在命令提示符中，用 `cd` 命令进入项目文件夹，例如：
   ```
   cd C:\Users\你的用户名\Downloads\每日提醒助手-基础版
   ```
2. 运行配置网页：
   ```
   python web_config.py
   ```
3. 看到提示后，打开浏览器访问 `http://localhost:5000`

### 第七步：在网页中完成配置

**学期设置**：
- 填写开学日期（格式：2026-03-02）
- 填写总周数（一般 16-18 周）
- 设置你的城市代码（[点这里查询城市代码](https://github.com/qwd/LocationList/blob/master/China-City-List-latest.csv)）

**课表管理**：
- 点击「上传课表」按钮，上传教务系统导出的 Excel 课表
- 或者手动添加课程

**每日提醒**：
- 选择是否跳过周末推送
- 添加你想要的每日提醒内容
- 推送时间默认为 23:30，如需修改请参见常见问题
**测试**：
- 点击「测试推送」验证配置是否正确

### 第八步：上传配置到 GitHub

配置完成后，需要把更新后的文件上传到 GitHub：

**需要上传的文件**：
- `config.json`（包含你的课表、学期设置等）

**上传方法**：

1. 在你的 GitHub 项目页面，点击 `config.json` 文件
2. 点击右上角的铅笔图标 ✏️ 进入编辑模式
3. 删除原有内容，复制本地 `config.json` 的全部内容粘贴进去
4. 点击右上角 **Commit changes** 保存

### 第九步：测试自动运行

1. 进入你的 GitHub 项目页面
2. 点击上方的 **Actions** 标签
3. 在左侧选择 **Daily Reminder**
4. 点击右侧 **Run workflow** → **Run workflow**
5. 等待运行完成，检查微信是否收到推送

---

## 常见问题

**Q: 没有收到推送？**
- 检查 GitHub Secrets 是否正确设置
- 检查 Actions 是否运行成功
- 检查 Server酱 SendKey 是否有效

**Q: 天气信息获取失败？**
- 检查城市代码是否正确
- 检查和风天气 API 是否有效

**Q: 如何修改推送时间？**

推送时间由 GitHub Actions 的 cron 表达式控制，修改步骤如下：

1. 进入你的 GitHub 项目页面
2. 打开 `.github/workflows/daily_reminder.yml` 文件
3. 点击右上角的铅笔图标 ✏️ 进入编辑模式
4. 找到这一行：`cron: '30 15 * * *'`
5. 修改时间（格式：`分 时 日 月 周`，使用 UTC 时间）

**时间换算**：
- 北京时间 = UTC + 8
- 例如：北京时间 21:00 = UTC 13:00
- 例如：北京时间 23:30 = UTC 15:30

**建议**：由于 GitHub Actions 用户量大，云端运行存在排队现象，建议将运行时间设置为目标时间提前 2-2.5 小时。例如希望 23:30 收到推送，可将 cron 设置为 `cron: '0 13 * * *'`（UTC 13:00 = 北京时间 21:00），这样实际推送时间会在 23:00-23:30 之间。

6. 修改完成后点击 **Commit changes** 保存

**Q: 周末不想收到推送？**
- 在配置网页的「每日提醒」中，选择「跳过周末」

---

## 文件说明

| 文件 | 说明 |
|-----|------|
| `config.json` | 主配置文件（课表、学期、提醒等） |
| `main.py` | 主程序 |
| `web_config.py` | 配置网页程序 |
| `requirements.txt` | Python 依赖列表 |
| `.env.example` | 环境变量模板 |
| `.github/workflows/daily_reminder.yml` | GitHub Actions 定时任务配置 |

---

## 许可证

MIT License
