# AutoCheckIn

赛尔号 17 周年活动页自动签到脚本。

## 使用

复制环境变量示例：

```powershell
Copy-Item .env.example .env
```

编辑 `.env` 填入账号密码，然后运行：

```powershell
docker compose run --rm autocheckin
```

脚本会把浏览器登录状态保存在 `./data/profile`，截图等诊断文件保存在 `./data/artifacts`。

## GitHub 和 Docker

本仓库带有 GitHub Actions workflow，会在 push 到 `main` 或手动运行时构建 Docker 镜像，并发布到 GitHub Container Registry：

```text
ghcr.io/Murmansk5000/seer17:latest
```

从远端镜像运行：

```powershell
docker run --rm `
  -e MIMI_ID=767448103 `
  -e MIMI_PASSWORD=your-password `
  -v ${PWD}/data:/data `
  ghcr.io/Murmansk5000/seer17:latest
```

## 第一次登录

第一次登录建议使用 GUI 模式。脚本会打开登录页、先尝试切到“米米号登录”，你只需要在浏览器里完成账号登录和滑块验证；登录成功后会话会保存在 `./data/profile`，之后普通定时运行不需要手动找 cookies。

本机运行：

```powershell
pip install -r requirements.txt
python -m playwright install chromium
$env:FIRST_LOGIN_GUI="true"
$env:HEADLESS="false"
python autocheckin.py
```

如果要用 Docker 做 GUI，需要宿主机提供图形显示环境；Windows Docker Desktop 默认容器窗口不会直接显示。更省事的做法是在本机先用上面的 GUI 模式完成一次登录，再让 Docker 复用同一个 `./data/profile`。

## 验证码

当前登录页可能出现“拖动下方拼图完成验证”。脚本不会绕过验证码；遇到验证码会截图并退出。通过一次登录后，后续可复用 `./data/profile` 中的会话继续签到。

## 环境变量

- `MIMI_ID`: 米米号
- `MIMI_PASSWORD`: 密码
- `HEADLESS`: 是否无头运行，默认 `true`
- `FIRST_LOGIN_GUI`: 首次登录 GUI 模式，默认 `false`
- `LOGIN_WAIT_SECONDS`: GUI 模式等待登录完成的秒数，默认 `300`
- `ALLOW_PASSWORD_LOGIN`: 是否尝试账号密码登录，默认 `true`
